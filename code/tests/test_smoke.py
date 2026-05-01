"""Quick sanity tests — run with: python -m pytest tests/test_smoke.py -v"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


# ─── Config sanity ────────────────────────────────────────────────────────

def test_allowed_status_values():
    assert config.ALLOWED_STATUS == {"replied", "escalated"}


def test_allowed_request_type_values():
    assert config.ALLOWED_REQUEST_TYPE == {"product_issue", "feature_request", "bug", "invalid"}


def test_temperature_is_zero():
    assert config.TEMPERATURE == 0.0


def test_seed_is_deterministic():
    assert config.SEED == 42


def test_models_are_set():
    assert config.TRIAGE_MODEL
    assert config.RESPONDER_MODEL
    assert config.FALLBACK_MODEL
    assert config.EMBEDDING_MODEL


def test_escalation_keywords_not_empty():
    assert len(config.ESCALATION_KEYWORDS) > 10


def test_thresholds_reasonable():
    assert 0.0 < config.MIN_SIMILARITY < 1.0
    assert config.CHUNK_SIZE > 100
    assert config.CHUNK_OVERLAP < config.CHUNK_SIZE
    assert config.TOP_K >= 3
    assert config.MAX_RESPONSE_CHARS >= 500
    assert config.MAX_JUSTIFICATION_CHARS >= 100


# ─── Index store exists ──────────────────────────────────────────────────

STORE_DIR = Path(__file__).resolve().parent.parent / "index" / "store"


def test_index_store_exists():
    assert STORE_DIR.exists(), f"Index store not found at {STORE_DIR}"
    assert (STORE_DIR / "embeddings.npy").exists()
    assert (STORE_DIR / "chunks.jsonl").exists()
    assert (STORE_DIR / "meta.json").exists()


def test_meta_json_valid():
    meta_path = STORE_DIR / "meta.json"
    if not meta_path.exists():
        return  # skip if index not built
    meta = json.loads(meta_path.read_text())
    assert "total_chunks" in meta
    assert meta["total_chunks"] > 0
    assert "per_company_counts" in meta
    assert "model_name" in meta
    assert meta["model_name"] == config.EMBEDDING_MODEL


def test_chunks_jsonl_valid():
    chunks_path = STORE_DIR / "chunks.jsonl"
    if not chunks_path.exists():
        return  # skip if index not built
    with open(chunks_path) as f:
        first_line = f.readline()
    chunk = json.loads(first_line)
    required_keys = {"id", "company", "source_path", "title", "text"}
    assert required_keys.issubset(chunk.keys()), f"Missing keys: {required_keys - chunk.keys()}"


# ─── Module imports ──────────────────────────────────────────────────────

def test_import_chunker():
    from index.chunker import chunk_text
    assert callable(chunk_text)


def test_import_retriever():
    from agent.retriever import Retriever
    assert Retriever is not None


def test_import_triage():
    from agent.triage import triage
    assert callable(triage)


def test_import_responder():
    from agent.responder import respond
    assert callable(respond)


def test_import_validator():
    from agent.validator import validate
    assert callable(validate)


def test_import_pipeline():
    from agent.pipeline import process_ticket
    assert callable(process_ticket)


def test_import_llm():
    from agent.llm import chat
    assert callable(chat)


# ─── Chunker basic functionality ─────────────────────────────────────────

def test_chunker_basic():
    from index.chunker import chunk_text
    text = "# Hello World\n\nThis is a test paragraph with enough content to be meaningful.\n\n## Section Two\n\nAnother paragraph here with more text to ensure we have enough for chunking."
    chunks = chunk_text(text, "test/file.md", "test_company")
    assert len(chunks) >= 1
    for chunk in chunks:
        assert "id" in chunk
        assert "company" in chunk
        assert chunk["company"] == "test_company"
        assert "source_path" in chunk
        assert "title" in chunk
        assert "text" in chunk
        assert len(chunk["text"]) > 0


# ─── Validator logic ─────────────────────────────────────────────────────

def test_validator_invalid_ticket():
    from agent.validator import validate
    ticket = {"subject": "", "issue": "asdf"}
    triage_out = {
        "preliminary_decision": "invalid",
        "request_type": "invalid",
        "reasoning": "Gibberish",
        "risk_flags": [],
        "company_inferred": "unknown",
    }
    result = validate(ticket, triage_out, [], None)
    assert result["status"] == "escalated"
    assert result["request_type"] == "invalid"


def test_validator_escalate_ticket():
    from agent.validator import validate
    ticket = {"subject": "Fraud", "issue": "Unauthorized charge"}
    triage_out = {
        "preliminary_decision": "escalate",
        "request_type": "product_issue",
        "reasoning": "Fraud detected",
        "risk_flags": ["fraud"],
        "company_inferred": "visa",
    }
    result = validate(ticket, triage_out, [], None)
    assert result["status"] == "escalated"
    assert "fraud" in result["response"].lower()


def test_validator_replied_ticket():
    from agent.validator import validate
    ticket = {"subject": "How to reset password", "issue": "I forgot my password"}
    triage_out = {
        "preliminary_decision": "proceed",
        "request_type": "product_issue",
        "reasoning": "Standard question",
        "risk_flags": [],
        "company_inferred": "claude",
    }
    retrieved = [{"score": 0.85, "id": "chunk-1"}]
    responder_out = {
        "response": "Go to login page and click forgot password.",
        "product_area": "account",
        "justification": "Covered by docs.",
        "cited_chunk_ids": ["chunk-1"],
        "grounded": True,
    }
    result = validate(ticket, triage_out, retrieved, responder_out)
    assert result["status"] == "replied"
    assert result["request_type"] == "product_issue"


def test_validator_ungrounded_escalates():
    from agent.validator import validate
    ticket = {"subject": "Question", "issue": "Something not in docs"}
    triage_out = {
        "preliminary_decision": "proceed",
        "request_type": "product_issue",
        "reasoning": "Proceed",
        "risk_flags": [],
        "company_inferred": "claude",
    }
    retrieved = [{"score": 0.5, "id": "chunk-1"}]
    responder_out = {
        "response": "Cannot answer safely.",
        "product_area": "unknown",
        "justification": "Not enough info.",
        "cited_chunk_ids": [],
        "grounded": False,
    }
    result = validate(ticket, triage_out, retrieved, responder_out)
    assert result["status"] == "escalated"


# ─── Output file checks ─────────────────────────────────────────────────

def test_output_csv_columns():
    import csv
    output_path = Path(__file__).resolve().parent.parent.parent / "support_tickets" / "output.csv"
    if not output_path.exists():
        return  # skip if not generated yet
    with open(output_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) > 0
    required = {"status", "product_area", "response", "justification", "request_type"}
    assert required.issubset(set(rows[0].keys())), f"Missing columns: {required - set(rows[0].keys())}"
    for row in rows:
        assert row["status"] in config.ALLOWED_STATUS, f"Bad status: {row['status']}"
        assert row["request_type"] in config.ALLOWED_REQUEST_TYPE, f"Bad type: {row['request_type']}"
        assert len(row["response"].strip()) > 0, "Empty response"
