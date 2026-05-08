"""
``text_summary`` 能力：文本摘要。

支持 ``mock`` / ``openai`` / ``anthropic`` 三种提供方（由环境变量 ``TEXT_SUMMARY_PROVIDER`` 决定）。
"""

from __future__ import annotations

import os
import re
import time
from typing import Any

from app.exceptions import CapabilityInvocationError


def _simulated_latency_ms() -> int:
    """
    读取模拟调用延迟（毫秒），仅 ``mock`` 模式使用。

    环境变量 ``AI_CAPABILITY_SIMULATED_LATENCY_MS``，非法值时回退为 3。
    """
    raw = os.environ.get("AI_CAPABILITY_SIMULATED_LATENCY_MS", "3")
    try:
        return max(0, int(raw))
    except ValueError:
        return 3


def _ensure_positive_int(value: Any, field: str) -> int:
    """
    校验 ``max_length`` 等字段为正整数（排除 ``bool``）。

    异常:
        CapabilityInvocationError: ``INVALID_INPUT``。
    """
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
    """
    本地模拟摘要：优先在 ``max_length`` 内拼接完整句，否则硬截断并加 ``...``。
    """
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


def _provider() -> str:
    """返回规范化后的 ``TEXT_SUMMARY_PROVIDER``，空则 ``mock``。"""
    p = os.environ.get("TEXT_SUMMARY_PROVIDER", "mock").strip().lower()
    return p or "mock"


def execute(inp: dict[str, Any]) -> str:
    """
    执行文本摘要：校验入参后按提供方调用 mock 或远程 LLM。

    参数:
        inp: 须含 ``text``；可选 ``max_length``（默认 120）。

    异常:
        CapabilityInvocationError: 入参错误、未知提供方、或上游/配置错误（由 LLM 层抛出）。
    """
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

    provider = _provider()
    if provider == "openai":
        from app.capabilities.llm_summary import summarize_openai

        return summarize_openai(text, max_length)
    if provider == "anthropic":
        from app.capabilities.llm_summary import summarize_anthropic

        return summarize_anthropic(text, max_length)
    if provider != "mock":
        raise CapabilityInvocationError(
            "CONFIG_ERROR",
            f'Unknown TEXT_SUMMARY_PROVIDER "{provider}"',
            {"allowed": ["mock", "openai", "anthropic"]},
        )

    delay = _simulated_latency_ms()
    if delay > 0:
        time.sleep(delay / 1000.0)

    return _first_units_within_budget(text, max_length)
