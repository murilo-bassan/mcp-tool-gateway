# ADR 0005 — A hash-chained, masked audit trail

**Status:** accepted

## Context
Auditors asked two questions a plain log table cannot answer: "was anything
deleted or edited?" and "did personal data end up in the logs?".

## Decision
- Each event stores `hash = sha256(prev_hash | canonical_json(event))`.
  `verify_chain()` walks the table and reports the first broken sequence number.
- Payloads are masked **before** they are hashed and stored (CPF/CNPJ keep their
  last digits, e-mails their domain; keys, tokens and anything under a
  secret-like key are blanked).

## Consequences
- Editing, deleting or reordering a row is detectable, and the panel shows it.
- Someone with DB write access could rewrite the entire tail consistently; anchoring
  the head hash outside the system (ticket, e-mail, object storage with retention)
  closes that gap and is a one-line operational habit.
- Because masking happens before hashing, the chain proves the masked record was
  not altered — the unmasked value is, by design, nowhere.
