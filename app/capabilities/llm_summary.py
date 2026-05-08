"""
通过 HTTP 调用 OpenAI / Anthropic 完成摘要，供 ``text_summary`` 在真实提供方下使用。
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from app.exceptions import CapabilityInvocationError

# 出站请求超时：读 60s，连接 10s。
_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


def _summary_user_prompt(text: str, max_length: int) -> str:
    """构造发给模型的用户提示词，约束输出为纯文本且不超过 ``max_length`` 字符。"""
    return (
        f"Summarize the following text in plain text only. "
        f"The summary must be at most {max_length} characters (including spaces). "
        f"Do not add quotes or a prefix.\n\n{text}"
    )


def _truncate_result(out: str, max_length: int) -> str:
    """去掉首尾空白后，若仍超长则截断并加省略号（与产品侧长度上限对齐）。"""
    out = out.strip()
    if not out:
        return out
    if len(out) <= max_length:
        return out
    if max_length <= 3:
        return out[:max_length]
    return out[: max_length - 3].rstrip() + "..."


def summarize_openai(text: str, max_length: int) -> str:
    """
    调用 OpenAI Chat Completions 生成摘要。

    依赖环境变量 ``OPENAI_API_KEY`` 等，失败时抛出 ``CONFIG_ERROR`` / ``UPSTREAM_ERROR``。
    """
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise CapabilityInvocationError(
            "CONFIG_ERROR",
            "OPENAI_API_KEY is required when TEXT_SUMMARY_PROVIDER=openai",
            {"provider": "openai"},
        )
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    url = f"{base}/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": _summary_user_prompt(text, max_length)}],
        "temperature": 0.3,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        snippet = (e.response.text or "")[:2000]
        raise CapabilityInvocationError(
            "UPSTREAM_ERROR",
            "OpenAI API returned an error",
            {"status_code": e.response.status_code, "body": snippet},
        ) from e
    except httpx.RequestError as e:
        raise CapabilityInvocationError(
            "UPSTREAM_ERROR",
            f"OpenAI request failed: {e!s}",
            {"provider": "openai"},
        ) from e

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise CapabilityInvocationError(
            "UPSTREAM_ERROR",
            "Unexpected OpenAI response shape",
            {"top_level_keys": list(data.keys()) if isinstance(data, dict) else None},
        ) from e
    if not isinstance(content, str):
        raise CapabilityInvocationError(
            "UPSTREAM_ERROR",
            "OpenAI message content was not a string",
            {},
        )
    return _truncate_result(content, max_length)


def _anthropic_extract_text(data: dict[str, Any]) -> str:
    """从 Anthropic Messages 响应的 ``content`` 数组中拼接 ``type==text`` 的文本。"""
    blocks = data.get("content")
    if not isinstance(blocks, list):
        raise CapabilityInvocationError(
            "UPSTREAM_ERROR",
            "Unexpected Anthropic response: content is not a list",
            {},
        )
    parts: list[str] = []
    for b in blocks:
        if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str):
            parts.append(b["text"])
    if not parts:
        raise CapabilityInvocationError(
            "UPSTREAM_ERROR",
            "Anthropic response contained no text blocks",
            {},
        )
    return "".join(parts)


def summarize_anthropic(text: str, max_length: int) -> str:
    """
    调用 Anthropic Messages（Claude）生成摘要。

    依赖 ``ANTHROPIC_API_KEY`` 等；错误语义同 ``summarize_openai``。
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise CapabilityInvocationError(
            "CONFIG_ERROR",
            "ANTHROPIC_API_KEY is required when TEXT_SUMMARY_PROVIDER=anthropic",
            {"provider": "anthropic"},
        )
    base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
    model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
    url = f"{base}/v1/messages"
    max_tokens = min(4096, max(256, max_length * 4))
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": _summary_user_prompt(text, max_length)}],
    }
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        snippet = (e.response.text or "")[:2000]
        raise CapabilityInvocationError(
            "UPSTREAM_ERROR",
            "Anthropic API returned an error",
            {"status_code": e.response.status_code, "body": snippet},
        ) from e
    except httpx.RequestError as e:
        raise CapabilityInvocationError(
            "UPSTREAM_ERROR",
            f"Anthropic request failed: {e!s}",
            {"provider": "anthropic"},
        ) from e

    if not isinstance(data, dict):
        raise CapabilityInvocationError("UPSTREAM_ERROR", "Anthropic response was not JSON object", {})
    raw = _anthropic_extract_text(data)
    return _truncate_result(raw, max_length)
