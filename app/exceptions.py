from __future__ import annotations


class CapabilityInvocationError(Exception):
    """Business error for capability run; maps to spec error payload."""

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)
