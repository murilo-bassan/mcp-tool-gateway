# toolgate

**English** · [Português](README.pt-BR.md)

A control panel for the tools an AI assistant can use. You decide who can use each tool,
passwords stay encrypted, and every call is logged so you can check later who did what.

![toolgate](docs/screenshots/chat-history.png)

## What you can do

- **Chat with the tools.** Ask "which grants are overdue in MS?" and the chat picks the right tool, asks for anything missing and explains the result. Conversations are saved.
- **Control who uses what.** Each role (admin, analyst, auditor) only sees the tools it is allowed to call.
- **Add new tools without touching code.** Register an HTTP endpoint in the panel; it only goes live after *another* person approves it.
- **Keep passwords and tokens safe.** They're encrypted and never shown back on screen.
- **Audit everything.** Each call becomes a log entry with personal data (tax ids, emails, cards) already masked. Entries are chained by hash, so you can tell if someone edited an old one.

Works with Claude Desktop or any MCP client, plus the web panel.

## Running it

```bash
git clone https://github.com/murilo-bassan/mcp-tool-gateway.git
cd mcp-tool-gateway
pip install -r requirements-dev.txt

python -m pytest                              # tests
python scripts/demo_traffic.py                # optional: sample activity
python -m uvicorn web.app:app --port 8600     # http://localhost:8600
```

Test logins: `admin/admin`, `analyst/analyst` and `auditor/auditor`. Also runs with `docker compose up --build`.

To use it in Claude Desktop, copy [`docs/claude_desktop_config.example.json`](docs/claude_desktop_config.example.json).
To try it from the terminal:

```bash
python scripts/mcp_call.py list
python scripts/mcp_call.py call invoices.validate_tax_id '{"tax_id": "11.222.333/0001-81"}'
```

The chat works without any model. To use an LLM, set `GATEWAY_LLM_API_KEY`, `GATEWAY_LLM_BASE_URL`
and `GATEWAY_LLM_MODEL` (any OpenAI-compatible API).

## How it works

Every call, whether it comes from Claude Desktop, the panel or another system, goes through the same path:
check permission, apply the rate limit, validate the arguments, run, log.
No entry point skips those steps.

```
gateway/
  executor.py   the single path for every call
  access.py     users, roles and permissions
  registry.py   tools registered from the panel
  audit.py      hash-chained log
  masking.py    personal data masking
  chat.py       the chat
  domains/      sample tools (invoices and grants)
server.py       MCP server
web/            web panel
```

Design decisions are in [`docs/adr`](docs/adr) and the security model in [`docs/security.md`](docs/security.md).

## Screens

| Console | Audit log |
|---|---|
| ![](docs/screenshots/console.png) | ![](docs/screenshots/audit.png) |
| **Registered tools** | **Permissions** |
| ![](docs/screenshots/registry.png) | ![](docs/screenshots/access.png) |

**Stack:** Python, FastAPI, MCP, SQLite, Docker

All data is made up. MIT license.
