"""Stage 1: Triage — classify ticket with a small fast LLM."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from agent.llm import chat

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "triage.md"
_TRIAGE_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def triage(ticket: dict) -> dict:
    """
    Classify a ticket.

    Input keys: subject, issue, company (str or None)
    Returns dict with: company_inferred, request_type, urgency,
                       risk_flags, preliminary_decision, reasoning
    """
    user_msg = json.dumps(
        {
            "subject": ticket.get("subject", ""),
            "issue": ticket.get("issue", ""),
            "company": ticket.get("company"),
        }
    )
    return chat(model=config.TRIAGE_MODEL, system=_TRIAGE_PROMPT, user=user_msg)


if __name__ == "__main__":
    import csv, random

    random.seed(config.SEED)
    sample_path = Path(__file__).resolve().parent.parent.parent / "support_tickets" / "sample_support_tickets.csv"
    with open(sample_path, newline="") as f:
        rows = list(csv.DictReader(f))

    samples = random.sample(rows, min(3, len(rows)))
    for row in samples:
        ticket = {"subject": row["subject"], "issue": row["issue"], "company": row["company"]}
        print("\nINPUT:", json.dumps(ticket, indent=2))
        result = triage(ticket)
        print("TRIAGE:", json.dumps(result, indent=2))
        print(f"  expected request_type={row['request_type']!r}  got={result.get('request_type')!r}")
