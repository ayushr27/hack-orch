"""Shared logging for the support triage agent.

All agent activity is appended to ~/hackerrank_orchestrate/log.txt
per AGENTS.md requirements.
"""

from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path.home() / "hackerrank_orchestrate"
LOG_FILE = LOG_DIR / "log.txt"
_log_dir_checked = False


def _ensure_log_dir() -> None:
    """Create log directory, handling edge cases where the path exists as a file."""
    global LOG_DIR, LOG_FILE, _log_dir_checked
    if _log_dir_checked:
        return
    try:
        if LOG_DIR.exists() and not LOG_DIR.is_dir():
            LOG_DIR.unlink()  # remove if it's a file/symlink
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Fallback: log in the project root if home dir is not writable
        LOG_DIR = Path(__file__).resolve().parent.parent / "hackerrank_orchestrate"
        LOG_FILE = LOG_DIR / "log.txt"
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    _log_dir_checked = True


def log(stage: str, ticket_id: str, message: str) -> None:
    """Append a structured log line per AGENTS.md spec.

    Format: [ISO8601] [STAGE] [ticket_id] message
    """
    _ensure_log_dir()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] [{stage}] [{ticket_id}] {message}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)
