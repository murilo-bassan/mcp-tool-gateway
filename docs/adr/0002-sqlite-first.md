# ADR 0002 — SQLite first, behind a narrow storage layer

**Status:** accepted

## Context
The gateway needs durable state (principals, secrets, tool revisions, audit
events) but must run as a single `git clone && python server.py` for evaluation,
and as a stdio subprocess of an MCP client where no database server exists.

## Decision
Use SQLite in WAL mode, one file under `GATEWAY_DATA_DIR`. Writes go through
`store.transaction()` (`BEGIN IMMEDIATE`) so concurrent writers serialize
instead of failing half-way — this matters for the audit chain, whose append
must read the tail and insert atomically.

## Consequences
- Zero infrastructure for demos, tests and local MCP use.
- One writer at a time. Fine for a gateway's write volume (mostly audit appends);
  a multi-replica deployment moves to Postgres. The companion repo
  `durable-agent-runtime` shows the Postgres version of these patterns
  (`FOR UPDATE SKIP LOCKED` queues, advisory locks).
- SQL is kept portable (no SQLite-only functions) to make that move mechanical.
