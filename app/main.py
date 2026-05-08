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
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = rid
    old = LOG.filters

    class InjectFilter(logging.Filter):
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
    return {
        "request_id": request_id,
        "capability": capability,
        "elapsed_ms": elapsed_ms,
    }


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
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
    return {"status": "ok"}


@app.post("/v1/capabilities/run")
async def run_capability_http(request: Request, payload: RunCapabilityRequest):
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
        status = 400 if e.code in {"INVALID_INPUT", "UNKNOWN_CAPABILITY"} else 500
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
