"""``text_echo`` 能力：原样回显文本，便于联调。"""

from __future__ import annotations

from typing import Any

from app.exceptions import CapabilityInvocationError


def execute(inp: dict[str, Any]) -> str:
    """
    将 ``input.text`` 原样返回。

    参数:
        inp: 须包含字符串字段 ``text``。

    异常:
        CapabilityInvocationError: 缺字段或类型错误（``INVALID_INPUT``）。
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
    return text
