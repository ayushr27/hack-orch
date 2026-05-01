"""Configuration for the support triage agent."""

import os

# ─── Models ──────────────────────────────────────────────────────────────
TRIAGE_MODEL = "llama-3.1-8b-instant"
RESPONDER_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "gemini-2.5-flash"

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ─── LLM call params ─────────────────────────────────────────────────────
TEMPERATURE = 0.0
MAX_TOKENS_TRIAGE = 400
MAX_TOKENS_RESPONDER = 1200
MAX_RETRIES = 4

# ─── Retrieval ───────────────────────────────────────────────────────────
TOP_K = 5
MIN_SIMILARITY = 0.35   # below this, validator escalates
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# ─── Output limits ───────────────────────────────────────────────────────
MAX_RESPONSE_CHARS = 1500
MAX_JUSTIFICATION_CHARS = 400

# ─── Determinism ─────────────────────────────────────────────────────────
SEED = 42

# ─── Paths ───────────────────────────────────────────────────────────────
DATA_DIR = "../data"
INDEX_DIR = "index/store"
SAMPLE_INPUT = "../support_tickets/sample_support_tickets.csv"
REAL_INPUT = "../support_tickets/support_tickets.csv"
OUTPUT_PATH = "../support_tickets/output.csv"

# ─── Escalation keywords (case-insensitive substring match on subject+issue) ───
ESCALATION_KEYWORDS = [
    # Fraud / security
    "unauthorized transaction", "unauthorized charge", "didn't make this charge",
    "stolen card", "lost my card", "card was stolen",
    "fraud", "fraudulent", "phishing", "scam",
    "account hacked", "account was hacked", "someone accessed my account",
    "compromised", "suspicious activity", "unrecognized login",

    # Financial disputes
    "chargeback", "dispute this charge", "wrong amount charged",
    "double charged", "refund denied",

    # Legal / data
    "lawyer", "legal action", "lawsuit", "sue you", "subpoena",
    "delete my data", "delete my account permanently", "right to be forgotten",
    "gdpr request", "ccpa request",

    # HackerRank specific
    "accused of cheating", "false plagiarism", "ai detection wrong",
    "academic integrity", "appeal my disqualification",

    # Claude specific
    "account suspended", "account banned", "permanently banned",

    # Distress
    "threaten", "harassed by", "abusive",
]

# ─── Invalid markers ─────────────────────────────────────────────────────
MIN_TICKET_CHARS = 8

# Allowed enums (validator enforces)
ALLOWED_STATUS = {"replied", "escalated"}
ALLOWED_REQUEST_TYPE = {"product_issue", "feature_request", "bug", "invalid"}

# ─── Env ─────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
