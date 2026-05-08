"""业务层异常：能力执行阶段的可预期错误，映射为 API 规范中的 ``error`` 结构。"""

from __future__ import annotations


class CapabilityInvocationError(Exception):
    """
    能力调用业务异常。

    由路由捕获后组装为 ``ok: false`` 的 JSON，并映射到对应 HTTP 状态码。
    """

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        """
        参数:
            code: 机器可读错误码（如 ``INVALID_INPUT``、``UPSTREAM_ERROR``）。
            message: 给人看的简短说明。
            details: 附加结构化信息，可为空。
        """
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)
