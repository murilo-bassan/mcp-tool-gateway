# ADR 0001 — One executor for every door

**Status:** accepted

## Context
Tools are reachable from three places: the stdio MCP server, the web panel,
and the service API (`/v1/call`). In an earlier design each entry point did its
own permission check and logging. They drifted: one forgot to mask, another
logged before validating.

## Decision
Every call, whatever the door, goes through `gateway.executor.execute`, which
does resolve → authorize → rate-limit → validate → run → audit, in that order.
Entry points only translate transport (JSON-RPC, HTTP) into a `Principal` and
a `(tool, arguments)` pair.

## Consequences
- A security fix lands once. A test of the executor covers all doors.
- Denials are audited the same way as successes — the trail shows attempts, not only effects.
- The panel has no privileged shortcut, which keeps "what the UI can do" equal to "what an API client can do".
