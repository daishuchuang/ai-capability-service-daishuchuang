from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RunCapabilityRequest(BaseModel):
    capability: str = Field(..., min_length=1, description="Registered capability name")
    input: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = Field(default=None, description="Optional idempotent trace id")


class SuccessMeta(BaseModel):
    request_id: str
    capability: str
    elapsed_ms: int


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class RunSuccessResponse(BaseModel):
    ok: Literal[True] = True
    data: dict[str, Any]
    meta: SuccessMeta


class RunErrorResponse(BaseModel):
    ok: Literal[False] = False
    error: ErrorBody
    meta: SuccessMeta
