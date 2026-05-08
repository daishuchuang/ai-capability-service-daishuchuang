from __future__ import annotations

import os
import re
import time
from typing import Any

from app.exceptions import CapabilityInvocationError


def _simulated_latency_ms() -> int:
    raw = os.environ.get("AI_CAPABILITY_SIMULATED_LATENCY_MS", "3")
    try:
        return max(0, int(raw))
    except ValueError:
        return 3


def _ensure_positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise CapabilityInvocationError(
            "INVALID_INPUT",
            f"{field} must be a positive integer",
            {"field": field, "got_type": "bool"},
        )
    if not isinstance(value, int):
        raise CapabilityInvocationError(
            "INVALID_INPUT",
            f"{field} must be a positive integer",
            {"field": field, "got_type": type(value).__name__},
        )
    if value < 1:
        raise CapabilityInvocationError(
            "INVALID_INPUT",
            f"{field} must be >= 1",
            {"field": field, "value": value},
        )
    return value


def _first_units_within_budget(text: str, max_length: int) -> str:
    """Prefer full sentences within max_length; otherwise hard truncate."""
    stripped = text.strip()
    if not stripped:
        return ""

    if len(stripped) <= max_length:
        return stripped

    # Split on sentence boundaries (EN/CN rough)
    parts = re.split(r"(?<=[.!?。！？])\s*", stripped)
    buf = ""
    for p in parts:
        if not p:
            continue
        candidate = (buf + " " + p).strip() if buf else p
        if len(candidate) <= max_length:
            buf = candidate
        else:
            break
    if buf:
        return buf

    if max_length <= 3:
        return stripped[:max_length]
    return stripped[: max_length - 3].rstrip() + "..."


def execute(inp: dict[str, Any]) -> str:
    if "text" not in inp:
        raise CapabilityInvocationError(
            "INVALID_INPUT",
            'input must contain string field "text"',
            {"missing": ["text"]},
        )
    text = inp["text"]
    if not isinstance(text, str):
        raise CapabilityInvocationError(
            "INVALID_INPUT",
            '"text" must be a string',
            {"field": "text", "got_type": type(text).__name__},
        )

    max_length = inp.get("max_length", 120)
    max_length = _ensure_positive_int(max_length, "max_length")

    delay = _simulated_latency_ms()
    if delay > 0:
        time.sleep(delay / 1000.0)

    return _first_units_within_budget(text, max_length)
