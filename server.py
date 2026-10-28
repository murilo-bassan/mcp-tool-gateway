"""MCP server (stdio). Exposes the catalog — native and approved dynamic tools — to any MCP client.

The low-level `Server` is used instead of decorators because tools here are
*data*: their JSON Schemas come from the registry at request time, so a tool
approved in the panel shows up on the client's next `tools/list` with no restart.

The stdio process acts as one principal (`GATEWAY_MCP_PRINCIPAL`), and only the
tools that principal's role allows are listed — the model never sees a tool it
would be denied.

    python server.py                       # serve on stdio
    python scripts/mcp_call.py list        # talk to it through the real protocol
"""
from __future__ import annotations

import json
import sys
from typing import Any

import anyio
import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from gateway import access, catalog, executor
from gateway.config import get_settings

INSTRUCTIONS = (
    "Governed tool gateway. Call meta.suggest_tool with the user's request when unsure which tool fits; "
    "call meta.list_tools to see everything you may use. Errors carry a stable `error` code and, for "
    "invalid_arguments, the JSON paths to fix."
)


def _principal() -> access.Principal:
    settings = get_settings()
    if settings.demo_seed:
        access.seed_demo()
    return access.get_principal(settings.mcp_principal)


def mcp_tools(principal: access.Principal) -> list[types.Tool]:
    return [
        types.Tool(
            name=t.name, title=t.title, description=t.description, input_schema=t.input_schema,
            annotations=types.ToolAnnotations(title=t.title, read_only_hint=t.read_only,
                                              destructive_hint=not t.read_only, open_world_hint=t.origin == "dynamic"),
        )
        for t in catalog.visible_to(principal.role.allows_tool)
    ]


def call(principal: access.Principal, name: str, arguments: dict[str, Any] | None) -> types.CallToolResult:
    outcome = executor.execute(principal, name, arguments or {})
    body = outcome.result if outcome.ok else outcome.error
    structured = body if isinstance(body, dict) else {"value": body}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(body, ensure_ascii=False, default=str))],
        structured_content=structured, is_error=not outcome.ok,
    )


def build_server() -> Server:
    principal = _principal()

    async def on_list_tools(ctx, params) -> types.ListToolsResult:
        return types.ListToolsResult(tools=mcp_tools(principal))

    async def on_call_tool(ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
        # Handlers are sync and may do I/O; keep the event loop free.
        return await anyio.to_thread.run_sync(call, principal, params.name, params.arguments)

    return Server("mcp-tool-gateway", version="0.1.0", instructions=INSTRUCTIONS,
                  on_list_tools=on_list_tools, on_call_tool=on_call_tool)


async def main() -> None:
    server = build_server()
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    try:
        anyio.run(main)
    except KeyboardInterrupt:
        sys.exit(0)
