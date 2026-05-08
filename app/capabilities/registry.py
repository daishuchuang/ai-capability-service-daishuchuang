from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.capabilities import text_echo, text_summary
from app.exceptions import CapabilityInvocationError

CapabilityFn = Callable[[dict[str, Any]], str]

CAPABILITY_REGISTRY: dict[str, CapabilityFn] = {
    "text_summary": text_summary.execute,
    "text_echo": text_echo.execute,
}


def run_capability(name: str, inp: dict[str, Any]) -> str:
    fn = CAPABILITY_REGISTRY.get(name)
    if fn is None:
        raise CapabilityInvocationError(
            "UNKNOWN_CAPABILITY",
            f'Unknown capability "{name}"',
            {"supported": sorted(CAPABILITY_REGISTRY.keys())},
        )
    return fn(inp)
