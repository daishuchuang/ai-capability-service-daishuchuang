"""
FastAPI 应用入口：健康检查、能力运行接口、校验错误格式与请求耗时统计。
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.capabilities.registry import run_capability
from app.exceptions import CapabilityInvocationError
from app.schemas import ErrorBody, RunCapabilityRequest, SuccessMeta

LOG = logging.getLogger("ai_capability_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时配置根日志格式。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    yield


app = FastAPI(
    title="AI Capability Service",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.middleware("http")
async def add_request_id_log_context(request: Request, call_next):
    """
    解析或生成 ``x-request-id``，写入 ``request.state`` 与响应头，并为日志注入 ``request_id``。
    """
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = rid

    class InjectFilter(logging.Filter):
        """将当前请求的 ``request_id`` 挂到 ``LogRecord`` 上供格式化使用。"""

        def filter(self, record: logging.LogRecord) -> bool:
            record.request_id = getattr(request.state, "request_id", "-")
            return True

    f = InjectFilter()
    LOG.addFilter(f)
    try:
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response
    finally:
        LOG.removeFilter(f)


def _meta(request_id: str, capability: str, elapsed_ms: int) -> dict[str, Any]:
    """构造响应体中的 ``meta`` 字典。"""
    return {
        "request_id": request_id,
        "capability": capability,
        "elapsed_ms": elapsed_ms,
    }


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    """将 Pydantic 校验错误转为题目约定的 ``VALIDATION_ERROR`` JSON（HTTP 422）。"""
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    errors = exc.errors()
    payload = {
        "ok": False,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request body failed validation",
            "details": {"errors": errors},
        },
        "meta": _meta(rid, "unknown", 0),
    }
    return JSONResponse(status_code=422, content=payload)


@app.get("/healthz")
def healthz():
    """存活探针，供编排或负载均衡使用。"""
    return {"status": "ok"}


@app.post("/v1/capabilities/run")
async def run_capability_http(request: Request, payload: RunCapabilityRequest):
    """
    统一能力调用入口：分发至注册表并包装成功/业务错误/未捕获异常响应。

    ``CapabilityInvocationError`` 映射到 400/502/503 等；其它异常为 500。
    """
    rid = payload.request_id or getattr(request.state, "request_id", str(uuid.uuid4()))
    t0 = time.perf_counter()
    try:
        result = run_capability(payload.capability, payload.input)
    except CapabilityInvocationError as e:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        LOG.warning(
            "capability_error request_id=%s code=%s capability=%s elapsed_ms=%s",
            rid,
            e.code,
            payload.capability,
            elapsed_ms,
        )
        error_status = {
            "INVALID_INPUT": 400,
            "UNKNOWN_CAPABILITY": 400,
            "UPSTREAM_ERROR": 502,
            "CONFIG_ERROR": 503,
        }
        status = error_status.get(e.code, 500)
        return JSONResponse(
            status_code=status,
            content={
                "ok": False,
                "error": ErrorBody(code=e.code, message=e.message, details=e.details).model_dump(),
                "meta": _meta(rid, payload.capability, elapsed_ms),
            },
        )
    except Exception:  # noqa: BLE001 — surface as internal for API contract
        LOG.exception("capability_run_failed request_id=%s capability=%s", rid, payload.capability)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected error while running capability",
                    "details": {},
                },
                "meta": _meta(rid, payload.capability, elapsed_ms),
            },
        )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    LOG.info(
        "capability_ok request_id=%s capability=%s elapsed_ms=%s",
        rid,
        payload.capability,
        elapsed_ms,
    )
    return {
        "ok": True,
        "data": {"result": result},
        "meta": SuccessMeta(
            request_id=rid,
            capability=payload.capability,
            elapsed_ms=elapsed_ms,
        ).model_dump(),
    }
