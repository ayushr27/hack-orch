"""LLM client: Groq primary (70B→8B fallback), then Gemini, with retry/backoff."""

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

_groq_client = None
_gemini_client = None


def _get_groq():
    global _groq_client
    if _groq_client is None:
        from openai import OpenAI
        _groq_client = OpenAI(
            api_key=os.environ.get("GROQ_API_KEY", config.GROQ_API_KEY),
            base_url=config.GROQ_BASE_URL,
        )
    return _groq_client


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY", config.GEMINI_API_KEY)
        )
    return _gemini_client


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


def _groq_call(model: str, system: str, user: str, max_tokens: int) -> dict:
    """Single Groq attempt, raises on any error."""
    client = _get_groq()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=config.TEMPERATURE,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        timeout=60,  # never hang more than 60s on a single request
    )
    return _parse_json(response.choices[0].message.content)


def _is_rate_limit(exc: Exception) -> bool:
    return any(kw in str(exc).lower() for kw in ("429", "rate", "quota", "token"))


def chat(
    model: str,
    system: str,
    user: str,
    json_mode: bool = True,
    max_retries: int = 4,
) -> dict:
    """
    Call LLMs with fallback chain:
      1. Requested model (e.g. llama-3.3-70b-versatile) with exponential backoff
      2. Groq llama-3.1-8b-instant (different quota, same fast infra)
      3. Gemini 2.5 Flash via google-genai SDK
    """
    is_triage = config.TRIAGE_MODEL in model or "8b" in model
    max_tokens = config.MAX_TOKENS_TRIAGE if is_triage else config.MAX_TOKENS_RESPONDER

    # ── Stage 1: primary model ────────────────────────────────────────────
    delay = 1.0
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return _groq_call(model, system, user, max_tokens)
        except Exception as exc:
            last_exc = exc
            if _is_rate_limit(exc):
                time.sleep(delay)
                delay = min(delay * 2, 30)
            else:
                break  # non-retryable — skip straight to fallbacks

    # ── Stage 2: Groq 8B fallback (only when primary was 70B) ────────────
    if model != config.TRIAGE_MODEL:
        try:
            return _groq_call(config.TRIAGE_MODEL, system, user, max_tokens)
        except Exception as exc:
            last_exc = exc

    # ── Stage 3: Gemini fallback ─────────────────────────────────────────
    try:
        from google import genai as _genai
        client = _get_gemini()
        prompt = f"SYSTEM:\n{system}\n\nUSER:\n{user}"
        if json_mode:
            prompt += "\n\nRespond with ONLY a valid JSON object. No markdown fences."
        resp = client.models.generate_content(
            model=config.FALLBACK_MODEL,
            contents=prompt,
            config={"http_options": {"timeout": 60}},
        )
        return _parse_json(resp.text)
    except Exception as fallback_exc:
        raise RuntimeError(
            f"All LLMs failed. Last Groq error: {last_exc}. "
            f"Gemini error: {fallback_exc}"
        ) from fallback_exc
