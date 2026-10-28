"""The one door every tool call goes through — from the MCP server and from the panel alike.

    resolve ─► authorize ─► rate-limit ─► validate args ─► run ─► audit
       │           │             │              │           │
    NotFound  PermissionDenied RateLimited InvalidArguments ToolFailed

Every outcome, including a denial, becomes one audit event. Arguments are
validated against the tool's JSON Schema *before* the handler runs, so a
handler can trust its input and an LLM gets a precise, path-level error to
correct itself with.
"""
from __future__ import annotations

import time
import uuid
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import BaseModel

from gateway import audit, catalog
from gateway.access import Principal
from gateway.catalog import CallContext
from gateway.config import get_settings
from gateway.errors import GatewayError, InvalidArguments, PermissionDenied, ToolFailed
from gateway.ratelimit import SlidingWindow


class CallOutcome(BaseModel):
    ok: bool
    tool: str
    correlation: str
    duration_ms: int
    result: Any = None
    error: dict[str, Any] | None = None


@lru_cache(maxsize=4)
def _limiter(limit: int) -> SlidingWindow:
    return SlidingWindow(limit=limit)


def _apply_defaults(schema: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    out = dict(args)
    for key, prop in schema.get("properties", {}).items():
        if key not in out and isinstance(prop, dict) and "default" in prop:
            out[key] = prop["default"]
    return out


def validate_arguments(schema: dict[str, Any], args: dict[str, Any]) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(args), key=lambda e: list(e.path))
    if errors:
        raise InvalidArguments("arguments do not match the tool's input schema", detail={
            "errors": [{"path": "/" + "/".join(map(str, e.path)), "message": e.message} for e in errors[:10]],
        })


def execute(principal: Principal, tool_name: str, arguments: dict[str, Any] | None = None,
            correlation: str | None = None) -> CallOutcome:
    correlation = correlation or uuid.uuid4().hex[:16]
    arguments = arguments or {}
    started = time.perf_counter()
    result: Any = None
    error: GatewayError | None = None
    try:
        spec = catalog.get(tool_name)
        if not principal.role.allows_tool(spec.name):
            raise PermissionDenied(f"role '{principal.role.name}' cannot call '{spec.name}'")
        _limiter(get_settings().rate_limit_per_min).check(principal.id)
        validate_arguments(spec.input_schema, arguments)
        result = spec.handler(_apply_defaults(spec.input_schema, arguments),
                              CallContext(principal_id=principal.id, correlation=correlation))
    except GatewayError as e:
        error = e
    except Exception as e:  # a handler bug must not leak a stack trace to the client
        error = ToolFailed(f"internal error in tool: {type(e).__name__}")
    duration = int((time.perf_counter() - started) * 1000)

    audit.record(audit.Event(
        kind="tool_call", actor=principal.id, tool=tool_name, correlation=correlation, duration_ms=duration,
        outcome="ok" if error is None else error.code,
        payload={"arguments": arguments, "error": error.as_dict() if error else None,
                 "result_preview": None if error else str(result)[:400]},
    ))
    return CallOutcome(ok=error is None, tool=tool_name, correlation=correlation, duration_ms=duration,
                       result=result if error is None else None, error=error.as_dict() if error else None)
