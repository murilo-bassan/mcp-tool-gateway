"""Minimal MCP client: spawns server.py over stdio and speaks the real protocol.

    python scripts/mcp_call.py list
    python scripts/mcp_call.py call invoices.validate_tax_id '{"tax_id": "11.222.333/0001-81"}'
    python scripts/mcp_call.py suggest "quais convênios estão atrasados em MS?"
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def run(argv: list[str]) -> int:
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if argv[0] == "list":
                for tool in (await session.list_tools()).tools:
                    print(f"{tool.name:34} {tool.title}")
                return 0
            if argv[0] == "suggest":
                argv = ["call", "meta.suggest_tool", json.dumps({"request": " ".join(argv[1:])})]
            if argv[0] == "call":
                args = json.loads(argv[2]) if len(argv) > 2 else {}
                result = await session.call_tool(argv[1], args)
                for block in result.content:
                    print(json.dumps(json.loads(block.text), indent=2, ensure_ascii=False))
                return 1 if result.is_error else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(anyio.run(run, sys.argv[1:]))
