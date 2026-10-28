# Security model

What the gateway defends against, how, and what it deliberately leaves to the platform.

| Threat | Control | Where |
|---|---|---|
| An LLM (or user) calls a tool it should not | Role globs checked on every call; tools outside the role are not even listed | `executor.py`, `catalog.visible_to`, `server.mcp_tools` |
| Malformed or malicious arguments reach a handler | JSON Schema (Draft 2020-12) validation before the handler runs; `additionalProperties: false` on native tools | `executor.validate_arguments` |
| Credentials leak into tool definitions, logs or the model context | Definitions may only reference `{{secret:name}}`; secrets are Fernet-encrypted at rest, resolved per caller at call time, listed by name only; audit payloads are masked | `registry.validate`, `secrets_store.py`, `masking.py` |
| SSRF through a registered HTTP tool | https only; literal private, loopback, link-local and reserved IPs rejected; redirects not followed; 1 MB response cap; timeouts | `registry._check_host`, `registry._handler` |
| A single person ships a risky integration | Four-eyes review: reviewer needs `registry.review` and cannot be the author | `registry.review` |
| Silent tampering with the audit trail | SHA-256 hash chain, verifiable from the panel and the API | `audit.verify_chain` |
| Personal data in logs | CPF, CNPJ, e-mail, phone, card, bearer/JWT/API-key patterns masked before storage; secret-named keys blanked | `masking.py` |
| Credential stuffing / enumeration | scrypt password hashes with per-user salt; same error for unknown user and wrong password; failed logins audited | `access.py`, `web/app.py` |
| CSRF against the panel | HttpOnly + SameSite=Strict cookie, plus a mandatory `X-Requested-With` header on every mutation | `web/app.py` |
| XSS / clickjacking in the panel | Strict CSP (`script-src 'self'`, `frame-ancestors 'none'`), DOM built with text nodes only, `X-Frame-Options: DENY` | `web/app.py`, `web/static/app.js` |
| Runaway client | Sliding-window rate limit per principal | `ratelimit.py` |
| Handler bugs leaking internals | Unexpected exceptions become `tool_failed` with the exception type only | `executor.execute` |

## Out of scope (by design)

- **DNS rebinding / hostname-based SSRF.** A public hostname that resolves to a private IP
  is caught by an egress proxy with an allowlist, not by string checks. Run dynamic tools
  behind one in production.
- **Multi-replica rate limiting.** The in-memory window is per process; move it to the
  database or Redis when running more than one replica.
- **Key rotation tooling.** `GATEWAY_SECRET_KEY` rotation means decrypt-with-old /
  encrypt-with-new over the `secrets` table; `MultiFernet` makes it a short script.
