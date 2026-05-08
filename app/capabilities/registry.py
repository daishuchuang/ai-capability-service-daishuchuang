"""能力名称到执行函数的注册与统一调度。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.capabilities import text_echo, text_summary
from app.exceptions import CapabilityInvocationError

# 单个能力入口：入参为 input 字典，返回字符串结果。
CapabilityFn = Callable[[dict[str, Any]], str]

# 能力名 -> 可调用对象；新增能力时在此登记。
CAPABILITY_REGISTRY: dict[str, CapabilityFn] = {
    "text_summary": text_summary.execute,
    "text_echo": text_echo.execute,
}


def run_capability(name: str, inp: dict[str, Any]) -> str:
    """
    按名称执行已注册能力。

    参数:
        name: ``capability`` 字段值。
        inp: 请求体中的 ``input`` 对象。

    返回:
        能力的文本结果，由路由包装进 ``data.result``。

    异常:
        CapabilityInvocationError: 未知能力名（``UNKNOWN_CAPABILITY``）。
    """
    fn = CAPABILITY_REGISTRY.get(name)
    if fn is None:
        raise CapabilityInvocationError(
            "UNKNOWN_CAPABILITY",
            f'Unknown capability "{name}"',
            {"supported": sorted(CAPABILITY_REGISTRY.keys())},
        )
    return fn(inp)
