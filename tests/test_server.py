import json
import os
import sys
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

import server
from gateway import access

ROOT = Path(__file__).resolve().parents[1]


def test_listing_is_filtered_by_role(isolated_settings):
    access.seed_demo()
    names = {t.name for t in server.mcp_tools(access.get_principal("auditor"))}
    assert names == {"meta.whoami", "meta.list_tools", "meta.suggest_tool"}
    admin_tools = server.mcp_tools(access.get_principal("admin"))
    review = next(t for t in admin_tools if t.name == "registry.review")
    assert review.annotations.destructive_hint is True


def test_call_maps_errors_to_is_error():
    access.seed_demo()
    result = server.call(access.get_principal("admin"), "invoices.get", {"id": "bad"})
    assert result.is_error and json.loads(result.content[0].text)["error"] == "invalid_arguments"


def test_end_to_end_over_stdio(tmp_path):
    """Spawns server.py and talks real MCP to it."""
    env = {**os.environ, "GATEWAY_DATA_DIR": str(tmp_path / "e2e"), "GATEWAY_DEMO_SEED": "true"}
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=str(ROOT), env=env)

    async def scenario():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = {t.name for t in (await session.list_tools()).tools}
                result = await session.call_tool("invoices.validate_tax_id", {"tax_id": "529.982.247-25"})
                return tools, json.loads(result.content[0].text)

    tools, payload = anyio.run(scenario)
    assert {"invoices.validate_tax_id", "grants.flag_risks", "registry.review"} <= tools
    assert payload == {"kind": "cpf", "valid": True}
