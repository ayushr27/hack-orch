# HackerRank Orchestrate — Support Triage Agent

## Overview

A terminal-based, 4-stage AI pipeline that triages support tickets for HackerRank, Claude, and Visa.
It reads an input CSV, classifies and routes each ticket, generates grounded responses from a local
knowledge corpus, and writes results to an output CSV. The system escalates to human agents when
it cannot safely answer.

## Setup

```bash
cd code
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GROQ_API_KEY and GEMINI_API_KEY
```

## Build the Index (one-time)

```bash
python -m index.build_index
```

This walks `data/{hackerrank,claude,visa}/`, chunks all markdown files, embeds them with
`sentence-transformers/all-MiniLM-L6-v2`, and saves artifacts to `index/store/`.

## Run

```bash
# Run on the sample file (with expected outputs for evaluation)
python main.py --in ../support_tickets/sample_support_tickets.csv \
               --out ../support_tickets/sample_output.csv

# Run on the real input
python main.py --in ../support_tickets/support_tickets.csv \
               --out ../support_tickets/output.csv

# Run with a limit (for testing)
python main.py --in ../support_tickets/support_tickets.csv \
               --out ../support_tickets/output.csv \
               --limit 10
```

## Architecture

```
┌────────┐   ┌──────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐
│ ticket │──>│ 1.Triage │──>│2.Retrieve │──>│3.Responder│──>│4.Validator│──> output row
└────────┘   └──────────┘   └───────────┘   └───────────┘   └───────────┘
                  │                                                 ▲
                  └─── if invalid/escalate-on-sight ────────────────┘
```

**Stage 1 — Triage** (Groq llama-3.1-8b-instant): classifies ticket, detects risk flags,
decides proceed/escalate/invalid.

**Stage 2 — Retrieve** (local, no LLM): embeds query, cosine similarity over corpus chunks
filtered by company.

**Stage 3 — Responder** (Groq llama-3.3-70b-versatile): generates grounded response citing
specific chunk IDs.

**Stage 4 — Validator** (deterministic): applies hard rules to determine final status and
normalize output schema.

## Design Decisions

- **Two model sizes**: Triage is classification (8B, fast, cheap); Responder needs reasoning (70B).
- **Local embeddings**: Deterministic, no rate limits, fits a static corpus. No API call needed.
- **numpy cosine similarity**: Corpus is small (<10K chunks); FAISS/Chroma would be overkill.
- **MIN_SIMILARITY = 0.35**: Prefer over-escalating to avoid hallucinated responses.
- **Gemini fallback**: If Groq rate-limits during eval, Gemini 2.5 Flash takes over.

## Determinism

- `temperature=0` on all LLM calls.
- `random.seed(42)` in main.
- All dependency versions pinned in `requirements.txt`.
- Embedding model version pinned.

## Known Limitations

- Multilingual tickets: `all-MiniLM-L6-v2` is English-tuned; non-English input will retrieve poorly.
- Over-escalation on worried-sounding but legitimate tickets.
- Corpus gaps: topics not in `data/` will always be escalated.
- Llama 70B occasionally adds trailing commentary after JSON; mitigated by JSON parsing retry.
- Free-tier Groq rate limits: 1,000 RPD for 70B model. Run in off-peak hours for large batches.

## Logging

All runs append to `~/hackerrank_orchestrate/log.txt` per AGENTS.md requirements.
