"""Stage 3: Responder — generate grounded response using 70B model."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from agent.llm import chat
from agent.retriever import Retriever

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "respond.md"
_RESPOND_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def respond(ticket: dict, retrieved_chunks: list[dict]) -> dict:
    """
    Generate a grounded response.

    Returns dict with: response, product_area, justification,
                       cited_chunk_ids, grounded
    """
    ticket_json = json.dumps(
        {
            "subject": ticket.get("subject", ""),
            "issue": ticket.get("issue", ""),
            "company": ticket.get("company"),
        }
    )

    context_parts = []
    for chunk in retrieved_chunks:
        context_parts.append(
            f"[chunk_id={chunk['id']}, source={chunk['source_path']}, title={chunk['title']}]\n{chunk['text']}"
        )

    user_msg = f"TICKET:\n{ticket_json}\n\nRETRIEVED CONTEXT:\n" + "\n\n".join(context_parts)

    return chat(model=config.RESPONDER_MODEL, system=_RESPOND_PROMPT, user=user_msg)


if __name__ == "__main__":
    import csv, random
    from pathlib import Path as P

    random.seed(config.SEED)
    store_dir = P(__file__).resolve().parent.parent / "index" / "store"
    retriever = Retriever(store_dir)

    sample_path = P(__file__).resolve().parent.parent.parent / "support_tickets" / "sample_support_tickets.csv"
    with open(sample_path, newline="") as f:
        rows = list(csv.DictReader(f))

    samples = [r for r in rows if r.get("status") == "replied"][:2]
    for row in samples:
        ticket = {"subject": row["subject"], "issue": row["issue"], "company": row["company"]}
        from agent.triage import triage
        triage_out = triage(ticket)
        company = triage_out.get("company_inferred")
        chunks = retriever.search(f"{row['subject']} {row['issue']}", company, k=config.TOP_K)
        print("\nTICKET:", ticket["subject"])
        result = respond(ticket, chunks)
        print("RESPOND:", json.dumps(result, indent=2))
