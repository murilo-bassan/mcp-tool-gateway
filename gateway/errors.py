"""Error types that cross module borders.

Each carries a stable `code`, which is what the MCP client and the panel see.
Messages are for humans; codes are for programs.
"""
from __future__ import annotations


class GatewayError(Exception):
    code = "gateway_error"

    def __init__(self, message: str, *, detail: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}

    def as_dict(self) -> dict:
        return {"error": self.code, "message": self.message, **({"detail": self.detail} if self.detail else {})}


class NotFound(GatewayError):
    code = "not_found"


class PermissionDenied(GatewayError):
    code = "permission_denied"


class InvalidArguments(GatewayError):
    code = "invalid_arguments"


class RateLimited(GatewayError):
    code = "rate_limited"


class ToolFailed(GatewayError):
    code = "tool_failed"


class InvalidDefinition(GatewayError):
    code = "invalid_definition"


class AuthFailed(GatewayError):
    code = "auth_failed"
