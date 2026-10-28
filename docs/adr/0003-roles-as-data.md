# ADR 0003 — Roles are data: tool globs + a closed set of admin permissions

**Status:** accepted

## Context
Hard-coded `if user.is_admin` checks made every access change a deploy, and
"which tools can this bot call?" had no single answer.

## Decision
A role is a row with two lists:
- `tool_globs` — fnmatch patterns over tool names (`grants.*`, `invoices.search`, `*`);
- `admin_perms` — from a **closed** set: `registry.write`, `registry.review`,
  `audit.read`, `secrets.write`, `access.admin`. Unknown permissions are rejected
  at write time, so a typo cannot silently grant nothing (or everything).

Tool listing is filtered by the same globs: an MCP client never sees a tool
its principal cannot call.

## Consequences
- Granting access is an operation in the panel, audited like any other.
- New tools inherit access through their domain prefix (`grants.*`).
- Globs are coarse by design; per-argument policies (e.g. "only state = MS") would
  belong in the tool or in a policy layer, not in roles.
