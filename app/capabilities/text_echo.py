from __future__ import annotations

from typing import Any

from app.exceptions import CapabilityInvocationError


def execute(inp: dict[str, Any]) -> str:
    """Bonus capability: echo text (useful for integration checks)."""
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
    return text
