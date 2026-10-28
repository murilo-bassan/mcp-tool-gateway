"""Meta tools: let a client (or an LLM) discover what it may do."""
from __future__ import annotations

from typing import Any

from gateway import access, catalog, intents
from gateway.catalog import CallContext, native, object_schema


def _visible(ctx: CallContext) -> list[catalog.ToolSpec]:
    role = access.get_principal(ctx.principal_id).role
    return catalog.visible_to(role.allows_tool)


@native("meta.whoami", title="Who am I", description="Your principal id, role and the tool patterns it grants.",
        schema=object_schema({}), keywords=("quem sou", "meu acesso", "permissoes", "whoami"))
def whoami(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    p = access.get_principal(ctx.principal_id)
    return {"id": p.id, "kind": p.kind, "role": p.role.name, "tool_globs": p.role.tool_globs,
            "admin_perms": p.role.admin_perms}


@native("meta.list_tools", title="List my tools",
        description="Every tool you may call, grouped by domain, with its input schema.",
        schema=object_schema({"domain": {"type": "string"}}), keywords=("listar tools", "o que posso", "ferramentas"))
def list_tools(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    tools = [t for t in _visible(ctx) if not args.get("domain") or t.domain == args["domain"]]
    by_domain: dict[str, list[dict]] = {}
    for t in tools:
        by_domain.setdefault(t.domain, []).append({"name": t.name, "title": t.title, "read_only": t.read_only})
    return {"count": len(tools), "domains": by_domain}


@native("meta.suggest_tool", title="Suggest a tool for a request",
        description="Ranks your tools for a natural-language request (PT or EN), deterministically, with the reasons.",
        schema=object_schema({"request": {"type": "string", "minLength": 3}, "top_k": {"type": "integer", "minimum": 1,
                                                                                     "maximum": 10}}, ["request"]),
        keywords=("qual ferramenta", "sugerir", "suggest"))
def suggest_tool(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    tools = [t for t in _visible(ctx) if not t.name.startswith("meta.")]
    hits = intents.suggest(args["request"], tools, top_k=args.get("top_k", 3))
    return {"request": args["request"],
            "suggestions": [{"tool": h.tool, "score": h.score, "reasons": list(h.reasons)} for h in hits]}
