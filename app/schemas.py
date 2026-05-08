"""Pydantic 请求/响应模型：与 OpenAPI 文档及入参校验对齐。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RunCapabilityRequest(BaseModel):
    """``POST /v1/capabilities/run`` 请求体。"""

    capability: str = Field(..., min_length=1, description="已注册的能力名称")
    input: dict[str, Any] = Field(default_factory=dict, description="该能力的入参对象")
    request_id: str | None = Field(default=None, description="可选，链路追踪 ID")


class SuccessMeta(BaseModel):
    """成功或失败响应中 ``meta`` 字段的公共结构。"""

    request_id: str
    capability: str
    elapsed_ms: int


class ErrorBody(BaseModel):
    """失败响应中 ``error`` 字段。"""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class RunSuccessResponse(BaseModel):
    """成功响应（文档/类型用；路由中多直接构造 dict）。"""

    ok: Literal[True] = True
    data: dict[str, Any]
    meta: SuccessMeta


class RunErrorResponse(BaseModel):
    """失败响应（文档/类型用）。"""

    ok: Literal[False] = False
    error: ErrorBody
    meta: SuccessMeta
