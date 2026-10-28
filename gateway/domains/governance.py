"""Registry tools: the governance flow, available to MCP clients as well as the panel."""
from __future__ import annotations

from typing import Any

from gateway import access, audit, registry
from gateway.catalog import CallContext, native, object_schema


def _event(ctx: CallContext, action: str, payload: dict[str, Any]) -> None:
    audit.record(audit.Event(kind="registry", actor=ctx.principal_id, outcome=action, correlation=ctx.correlation,
                             payload=payload))


@native("registry.list", title="List dynamic tools", description="Every dynamic tool revision, optionally filtered by status.",
        schema=object_schema({"status": {"enum": ["draft", "approved", "disabled", "superseded"]}}))
def list_definitions(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    revs = registry.list_revisions(args.get("status"))
    return {"items": [{"name": r.name, "revision": r.revision, "status": r.status, "author": r.author,
                       "reviewer": r.reviewer, "url": r.definition.http.url} for r in revs]}


@native("registry.propose", title="Propose a dynamic tool",
        description="Submits an HTTP tool definition as a draft. It runs only after another person approves it.",
        schema=object_schema({"definition": {"type": "object"}}, ["definition"]), read_only=False)
def propose(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    defn = registry.DynamicToolDefinition.model_validate(args["definition"])
    rev = registry.propose(defn, access.get_principal(ctx.principal_id))
    _event(ctx, "proposed", {"name": rev.name, "revision": rev.revision})
    return {"name": rev.name, "revision": rev.revision, "status": rev.status}


@native("registry.review", title="Approve or reject a draft",
        description="Four-eyes review of a draft revision. The author cannot review their own tool.",
        schema=object_schema({"name": {"type": "string"}, "revision": {"type": "integer", "minimum": 1},
                              "approve": {"type": "boolean"}}, ["name", "revision", "approve"]), read_only=False)
def review(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    rev = registry.review(args["name"], args["revision"], access.get_principal(ctx.principal_id), args["approve"])
    _event(ctx, "approved" if args["approve"] else "rejected", {"name": rev.name, "revision": rev.revision})
    return {"name": rev.name, "revision": rev.revision, "status": rev.status}
