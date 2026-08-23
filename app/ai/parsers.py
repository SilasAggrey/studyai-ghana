"""Robust extraction of JSON from LLM output.

Models frequently wrap JSON in ```json fences or add trailing prose. These
helpers find the first JSON value and parse it instead of failing outright.
"""
import json
import logging
import re

from app.ai.base import AIProviderError

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> object:
    """Return the first JSON value found in `text`, else raise AIProviderError."""
    if not text:
        raise AIProviderError("Empty model response while expecting JSON.")

    fence = _FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()

    text = text.strip()
    # Find the outermost JSON object or array.
    start_candidates = [text.find("{"), text.find("[")]
    start_candidates = [s for s in start_candidates if s != -1]
    if not start_candidates:
        raise AIProviderError("No JSON found in model response.")
    start = min(start_candidates)
    end = _find_json_end(text, start)
    if end is None:
        raise AIProviderError("Unterminated JSON in model response.")

    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError as exc:
        raise AIProviderError(f"Model returned invalid JSON: {exc}") from exc


def _find_json_end(text: str, start: int) -> int | None:
    """Find the index just past the matching closing brace/bracket."""
    open_ch = text[start]
    close_ch = "]" if open_ch == "[" else "}"
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
    return None


def extract_json_array(text: str) -> list:
    value = extract_json(text)
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        # Some models wrap the array: {"questions": [...]}
        for key in ("questions", "items", "data", "results"):
            if isinstance(value.get(key), list):
                return value[key]
    raise AIProviderError("Model response is not a JSON array of questions.")
