"""Thin client for the one real LLM call in the pipeline: confidence scoring.

Every other agent is deterministic on purpose (money/dates/IDs have a single
correct answer, and an LLM only adds risk there). Confidence is the one field
where a model's judgment is an acceptable input, so this is where
`agents/config.MODEL_NAME` actually gets called instead of just being declared.

Any failure (Ollama not running, timeout, unparseable reply) returns None so
the caller can fall back to the heuristic — a case must never fail to process
just because the model was slow or unavailable.
"""

from __future__ import annotations

import os
import re

import httpx
from dotenv import load_dotenv

from .config import DEFAULT_OPENAI_HOST, MODEL_NAME

load_dotenv()

_NUMBER_RE = re.compile(r"(\d*\.?\d+)")
# Ollama unloads an idle model after a few minutes; the first call after that
# needs ~20-30s just to reload weights on this CPU-only machine before it can
# even start generating, so the timeout must cover a cold start, not only a
# warm one (~1s).
_TIMEOUT_SECONDS = 45.0


def score_confidence(prompt: str, host: str = DEFAULT_OPENAI_HOST) -> float | None:
    """Ask the model for a single confidence number in [0, 1]. None on any failure."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY is not set. Ensure it is added to .env.")
        return None

    try:
        response = httpx.post(
            f"{host}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, ValueError, IndexError):
        return None

    match = _NUMBER_RE.search(text)
    if not match:
        return None

    try:
        value = float(match.group(1))
    except ValueError:
        return None

    if not (0.0 <= value <= 1.0):
        return None

    return round(value, 2)
