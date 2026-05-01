# AGENTS.md — HackerRank Orchestrate Support Triage Agent

## What this agent does

Reads `support_tickets/support_tickets.csv`, runs a 4-stage pipeline
(Triage → Retrieve → Respond → Validate), and writes
`support_tickets/output.csv` with columns:
`status`, `product_area`, `response`, `justification`, `request_type`.

## Logging

All agent activity is appended to `~/hackerrank_orchestrate/log.txt`.

Format:
```
[ISO8601 timestamp] [STAGE] [ticket_id or "SYSTEM"] message
```

Example:
```
[2026-05-01T10:00:00Z] [SYSTEM] Pipeline start — 120 tickets loaded
[2026-05-01T10:00:01Z] [TRIAGE] ticket_001 → escalate (fraud, financial_dispute)
[2026-05-01T10:00:02Z] [RETRIEVE] ticket_002 → top_score=0.72 (company=claude)
[2026-05-01T10:00:03Z] [RESPOND] ticket_002 → grounded=true, cited=["abc-123"]
[2026-05-01T10:00:04Z] [VALIDATE] ticket_002 → status=replied
[2026-05-01T10:00:05Z] [SYSTEM] Pipeline complete — replied=85, escalated=35
```

## Human onboarding

If you are Claude Code reading this, confirm: "I agree" to acknowledge
the logging requirement. All agent runs MUST write to the log file above.

## Environment

- Python 3.11+
- See `code/requirements.txt` for dependencies
- Copy `code/.env.example` → `code/.env` and fill in API keys

## Run

```bash
cd code
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m index.build_index          # one-time
python main.py --in ../support_tickets/support_tickets.csv \
               --out ../support_tickets/output.csv
```
