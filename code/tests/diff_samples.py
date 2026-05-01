"""Compare sample_output.csv against sample_support_tickets.csv (which has expected outputs).

Uses the same SentenceTransformer embedder for cosine similarity on responses,
per the implementation plan.
"""

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

SAMPLE_PATH = Path(__file__).resolve().parent.parent.parent / "support_tickets" / "sample_support_tickets.csv"
OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "support_tickets" / "sample_output.csv"


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _load_embedder():
    """Load the same SentenceTransformer used at index time."""
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(config.EMBEDDING_MODEL)
    except ImportError:
        return None


def cosine_sim_embedding(model, a: str, b: str) -> float:
    """Compute cosine similarity between two strings using the embedding model."""
    if not a.strip() or not b.strip():
        return 0.0
    embs = model.encode([a, b], convert_to_numpy=True, normalize_embeddings=True)
    return float(np.dot(embs[0], embs[1]))


def cosine_sim_token(a: str, b: str) -> float:
    """Fallback: rough token overlap similarity."""
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))


def main():
    if not SAMPLE_PATH.exists():
        print(f"Sample file not found: {SAMPLE_PATH}")
        sys.exit(1)
    if not OUTPUT_PATH.exists():
        print(f"Output file not found: {OUTPUT_PATH}")
        print("Run: python main.py --in ../support_tickets/sample_support_tickets.csv --out ../support_tickets/sample_output.csv")
        sys.exit(1)

    expected = {r["ticket_id"]: r for r in load_csv(SAMPLE_PATH)}
    predicted = {r["ticket_id"]: r for r in load_csv(OUTPUT_PATH)}

    ids = sorted(set(expected) & set(predicted))
    if not ids:
        print("No matching ticket_ids between sample and output files.")
        sys.exit(1)

    # Try to load the real embedder; fall back to token overlap
    model = _load_embedder()
    sim_method = "embedding" if model else "token_overlap"
    if model:
        print(f"Using SentenceTransformer ({config.EMBEDDING_MODEL}) for response similarity\n")
    else:
        print("SentenceTransformer not available — falling back to token overlap similarity\n")

    status_match = 0
    type_match = 0
    response_sims = []
    mismatches = []

    print(f"{'ID':<8} {'status':>8} {'type':>16} {'resp_sim':>9}  notes")
    print("-" * 70)

    for tid in ids:
        exp = expected[tid]
        pred = predicted[tid]

        s_ok = exp.get("status", "") == pred.get("status", "")
        t_ok = exp.get("request_type", "").lower() == pred.get("request_type", "").lower()

        if model:
            sim = cosine_sim_embedding(model, exp.get("response", ""), pred.get("response", ""))
        else:
            sim = cosine_sim_token(exp.get("response", ""), pred.get("response", ""))

        if s_ok:
            status_match += 1
        if t_ok:
            type_match += 1
        response_sims.append(sim)

        notes = []
        if not s_ok:
            notes.append(f"status: expected={exp.get('status')!r} got={pred.get('status')!r}")
        if not t_ok:
            notes.append(f"type: expected={exp.get('request_type')!r} got={pred.get('request_type')!r}")
        if sim < 0.6:
            notes.append(f"low response similarity ({sim:.2f})")

        # Check product_area (case-insensitive partial match)
        exp_pa = (exp.get("product_area") or "").lower()
        pred_pa = (pred.get("product_area") or "").lower()
        if exp_pa and pred_pa and exp_pa not in pred_pa and pred_pa not in exp_pa:
            notes.append(f"product_area: expected={exp_pa!r} got={pred_pa!r}")

        # Justification length sanity
        just_len = len(pred.get("justification", ""))
        if just_len < 10:
            notes.append(f"justification too short ({just_len} chars)")
        elif just_len > config.MAX_JUSTIFICATION_CHARS + 50:
            notes.append(f"justification too long ({just_len} chars)")

        flag = "✓" if s_ok and t_ok and sim >= 0.3 else "✗"
        print(f"{tid:<8} {'OK' if s_ok else 'FAIL':>8} {'OK' if t_ok else 'FAIL':>16} {sim:>9.2f}  {flag} {'; '.join(notes)}")

        if notes:
            mismatches.append({"id": tid, "notes": notes, "expected": exp, "predicted": pred})

    n = len(ids)
    mean_sim = sum(response_sims) / n if n else 0.0

    print()
    print(f"=== Aggregate ({sim_method}) ===")
    print(f"Status accuracy   : {status_match}/{n} ({100*status_match/n:.1f}%)")
    print(f"Req type accuracy : {type_match}/{n} ({100*type_match/n:.1f}%)")
    print(f"Mean resp sim     : {mean_sim:.3f}")

    if mismatches:
        print(f"\n=== {len(mismatches)} mismatched rows ===")
        for m in mismatches:
            print(f"\n[{m['id']}]")
            for note in m["notes"]:
                print(f"  • {note}")


if __name__ == "__main__":
    main()
