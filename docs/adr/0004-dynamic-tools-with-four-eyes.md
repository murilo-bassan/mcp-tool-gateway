# ADR 0004 — Dynamic tools are data, approved by a second person

**Status:** accepted

## Context
Analysts kept asking for "just one more endpoint" as an LLM tool. Shipping each
as code was slow; letting anyone register arbitrary HTTP calls is an SSRF and
credential-leak machine with an LLM attached.

## Decision
A dynamic tool is a versioned definition (JSON Schema + HTTP binding). It is
validated mechanically at proposal time — schema validity, https only, no
private/link-local addresses, every URL placeholder declared in the schema, no
literal credentials (only `{{secret:name}}` references) — and becomes callable
only after review by someone with `registry.review` **who is not the author**.

Approving a new revision supersedes the previous one; history is kept.

## Consequences
- New integrations ship in minutes, with a reviewer on record and an audit event.
- Secrets are resolved at call time per caller, so one definition serves many
  users with their own keys, and no plaintext reaches the catalog or the LLM.
- DNS-based SSRF (a public hostname resolving to a private IP) is out of scope
  here and belongs to an egress proxy — see `docs/security.md`.
