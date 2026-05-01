"""Stage 4: Validator — apply hard rules to finalize status and normalize output."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def _contains_escalation_keyword(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in config.ESCALATION_KEYWORDS)


def _truncate(s: str, max_len: int) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_len] if len(s) > max_len else s


def _normalize_request_type(rt: str) -> str:
    rt = (rt or "").lower().strip()
    if rt in config.ALLOWED_REQUEST_TYPE:
        return rt
    if "feature" in rt:
        return "feature_request"
    if "bug" in rt:
        return "bug"
    if "invalid" in rt:
        return "invalid"
    return "product_issue"


def validate(
    ticket: dict,
    triage_out: dict,
    retrieved: list[dict],
    responder_out: dict | None,
) -> dict:
    """
    Return the final 5-column output row.
    {status, product_area, response, justification, request_type}
    First matching rule wins for status.
    """
    decision = triage_out.get("preliminary_decision", "proceed")
    request_type = _normalize_request_type(triage_out.get("request_type", "product_issue"))
    triage_reasoning = triage_out.get("reasoning", "")
    risk_flags = triage_out.get("risk_flags", [])
    company_inferred = triage_out.get("company_inferred", "unknown")

    subject = ticket.get("subject", "")
    issue = ticket.get("issue", "")
    combined_text = f"{subject} {issue}"

    def _escalate(response: str, product_area: str, justification: str) -> dict:
        return {
            "status": "escalated",
            "product_area": _truncate(product_area, 80),
            "response": _truncate(response, config.MAX_RESPONSE_CHARS),
            "justification": _truncate(justification, config.MAX_JUSTIFICATION_CHARS),
            "request_type": request_type,
        }

    # Rule 1: invalid ticket
    if decision == "invalid":
        return _escalate(
            response="This ticket does not appear to be a valid support request. If you have a real issue, please submit a new ticket with a clear description.",
            product_area="out_of_scope",
            justification=triage_reasoning or "Not an actionable support request.",
        )

    # Rule 2: triage said escalate
    if decision == "escalate":
        flags_str = ", ".join(risk_flags) if risk_flags else "policy"
        return _escalate(
            response=f"This ticket has been escalated to a human specialist due to: {flags_str}.",
            product_area=f"{company_inferred}:sensitive" if company_inferred != "unknown" else "sensitive",
            justification=triage_reasoning or "Escalation required by triage policy.",
        )

    # Rule 3: responder not available
    if responder_out is None:
        return _escalate(
            response="Unable to generate an automated response for this ticket. A human agent will follow up.",
            product_area=company_inferred,
            justification="Responder stage was skipped or failed.",
        )

    # Rule 4: responder not grounded
    if not responder_out.get("grounded", True):
        return _escalate(
            response="Insufficient documentation to answer safely; routing to a human agent.",
            product_area=responder_out.get("product_area") or "unknown",
            justification="Retrieval did not surface authoritative content for this query.",
        )

    # Rule 5: low retrieval similarity
    max_score = max((c.get("score", 0.0) for c in retrieved), default=0.0)
    if max_score < config.MIN_SIMILARITY:
        return _escalate(
            response="The available documentation does not closely match this query. A human agent will follow up.",
            product_area=responder_out.get("product_area") or "unknown",
            justification=f"Max retrieval similarity {max_score:.3f} below threshold {config.MIN_SIMILARITY}.",
        )

    # Rule 6: no citations
    if not responder_out.get("cited_chunk_ids"):
        return _escalate(
            response="Insufficient documentation to answer safely; routing to a human agent.",
            product_area=responder_out.get("product_area") or "unknown",
            justification="Responder returned no cited chunk IDs.",
        )

    # Rule 7: escalation keyword in ticket text
    if _contains_escalation_keyword(combined_text):
        flags_str = ", ".join(risk_flags) if risk_flags else "keyword match"
        return _escalate(
            response=f"This ticket has been escalated to a human specialist due to: {flags_str}.",
            product_area=responder_out.get("product_area") or company_inferred,
            justification="Escalation keyword detected in ticket text.",
        )

    # Rule 8: all checks passed → replied
    return {
        "status": "replied",
        "product_area": _truncate(responder_out.get("product_area") or company_inferred, 80),
        "response": _truncate(responder_out.get("response", ""), config.MAX_RESPONSE_CHARS),
        "justification": _truncate(responder_out.get("justification", ""), config.MAX_JUSTIFICATION_CHARS),
        "request_type": request_type,
    }
