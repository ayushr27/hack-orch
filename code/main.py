"""CLI entry: python main.py --in <csv> --out <csv> [--limit N]"""

import argparse
import csv
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv(Path(__file__).resolve().parent / ".env")

import config
from agent.pipeline import process_ticket
from agent.retriever import Retriever

random.seed(config.SEED)

LOG_DIR = None  # set after first log call, for display in summary
LOG_FILE = None

OUTPUT_COLUMNS = ["ticket_id", "company", "subject", "issue",
                  "status", "product_area", "response", "justification", "request_type"]


def _log(stage: str, ticket_id: str, message: str) -> None:
    global LOG_DIR, LOG_FILE
    from agent.logger import log, LOG_DIR as _ld, LOG_FILE as _lf
    log(stage, ticket_id, message)
    LOG_DIR = _ld
    LOG_FILE = _lf


def main() -> None:
    parser = argparse.ArgumentParser(description="Support triage agent")
    parser.add_argument("--in", dest="input_path", default=config.REAL_INPUT)
    parser.add_argument("--out", dest="output_path", default=config.OUTPUT_PATH)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)

    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if args.limit:
        rows = rows[: args.limit]

    _log("SYSTEM", "SYSTEM", f"Pipeline start — {len(rows)} tickets loaded from {input_path}")

    store_dir = Path(__file__).resolve().parent / "index" / "store"
    retriever = Retriever(store_dir)

    output_rows = []
    trace_rows = []
    status_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    sim_scores: list[float] = []

    for row in tqdm(rows, desc="Processing tickets"):
        ticket_id = row.get("ticket_id", "unknown")
        ticket = {
            "ticket_id": ticket_id,
            "company": row.get("company"),
            "subject": row.get("subject", ""),
            "issue": row.get("issue", ""),
        }

        result = process_ticket(ticket, retriever)

        _log("VALIDATE", ticket_id, f"status={result.get('status')} request_type={result.get('request_type')} product_area={result.get('product_area')}")

        out_row = {col: row.get(col, "") for col in ["ticket_id", "company", "subject", "issue"]}
        out_row.update({
            "status": result.get("status", "escalated"),
            "product_area": result.get("product_area", "unknown"),
            "response": result.get("response", ""),
            "justification": result.get("justification", ""),
            "request_type": result.get("request_type", "product_issue"),
        })
        output_rows.append(out_row)

        st = out_row["status"]
        rt = out_row["request_type"]
        status_counts[st] = status_counts.get(st, 0) + 1
        type_counts[rt] = type_counts.get(rt, 0) + 1

        if "max_sim" in result:
            sim_scores.append(result["max_sim"])

        trace_rows.append({"ticket_id": ticket_id, **result})

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine column order: match sample file if possible
    fieldnames = [c for c in OUTPUT_COLUMNS if c in output_rows[0]] if output_rows else OUTPUT_COLUMNS

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output_rows)

    sidecar = output_path.with_suffix(".jsonl")
    with open(sidecar, "w") as f:
        for t in trace_rows:
            f.write(json.dumps(t) + "\n")

    mean_sim = sum(sim_scores) / len(sim_scores) if sim_scores else float("nan")
    summary_msg = (
        f"Pipeline complete — "
        + ", ".join(f"{k}={v}" for k, v in sorted(status_counts.items()))
        + " | "
        + ", ".join(f"{k}={v}" for k, v in sorted(type_counts.items()))
        + f" | mean_sim={mean_sim:.3f}"
    )
    _log("SYSTEM", "SYSTEM", summary_msg)

    print(f"\n=== Summary ===")
    print(f"Output: {output_path}")
    print(f"Status : {status_counts}")
    print(f"Type   : {type_counts}")
    if sim_scores:
        print(f"Mean retrieval similarity: {mean_sim:.3f}")
    print(f"Log    : {LOG_FILE}")


if __name__ == "__main__":
    main()
