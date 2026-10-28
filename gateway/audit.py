"""Tamper-evident audit trail.

Every event stores `hash = sha256(prev_hash | canonical(event))`. Editing,
deleting or reordering any past row breaks every hash after it, and
`verify_chain()` reports the first broken sequence number. It is not a
blockchain — someone with write access can rewrite the whole tail — but it
turns silent tampering into a detectable one, which is what an auditor asks for.
Anchoring the latest hash somewhere else (a ticket, an e-mail) closes that gap.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from gateway import masking, store

EventKind = Literal["tool_call", "login", "registry", "secret", "access"]


class Event(BaseModel):
    kind: EventKind
    actor: str | None = None
    tool: str | None = None
    outcome: str | None = None
    duration_ms: int | None = None
    correlation: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class StoredEvent(Event):
    seq: int
    id: str
    ts: float
    prev_hash: str | None
    hash: str


def _canonical(event_id: str, ts: float, event: Event, payload_json: str) -> str:
    body = {
        "id": event_id, "ts": round(ts, 6), "kind": event.kind, "actor": event.actor, "tool": event.tool,
        "outcome": event.outcome, "duration_ms": event.duration_ms, "correlation": event.correlation,
        "payload": payload_json,
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def chain_hash(prev_hash: str | None, canonical: str) -> str:
    return hashlib.sha256(f"{prev_hash or 'genesis'}|{canonical}".encode()).hexdigest()


def record(event: Event) -> str:
    """Masks, chains and stores one event. Returns its id."""
    event_id = uuid.uuid4().hex
    ts = time.time()
    payload_json = json.dumps(masking.mask(event.payload), sort_keys=True, ensure_ascii=False, default=str)
    with store.transaction() as conn:  # BEGIN IMMEDIATE: reading the tail and appending are atomic
        row = conn.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        prev = row["hash"] if row else None
        digest = chain_hash(prev, _canonical(event_id, ts, event, payload_json))
        conn.execute(
            "INSERT INTO events (id, ts, kind, actor, tool, outcome, duration_ms, correlation, payload, prev_hash, hash)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, ts, event.kind, event.actor, event.tool, event.outcome, event.duration_ms,
             event.correlation, payload_json, prev, digest),
        )
    return event_id


def _row_to_event(row: Any) -> StoredEvent:
    return StoredEvent(
        seq=row["seq"], id=row["id"], ts=row["ts"], kind=row["kind"], actor=row["actor"], tool=row["tool"],
        outcome=row["outcome"], duration_ms=row["duration_ms"], correlation=row["correlation"],
        payload=json.loads(row["payload"]), prev_hash=row["prev_hash"], hash=row["hash"],
    )


def search(kind: EventKind | None = None, actor: str | None = None, tool: str | None = None,
           limit: int = 200) -> list[StoredEvent]:
    clauses, params = [], []
    for column, value in (("kind", kind), ("actor", actor), ("tool", tool)):
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with store.reading() as conn:
        rows = conn.execute(f"SELECT * FROM events {where} ORDER BY seq DESC LIMIT ?", (*params, limit)).fetchall()
    return [_row_to_event(r) for r in rows]


def correlated(correlation: str) -> list[StoredEvent]:
    with store.reading() as conn:
        rows = conn.execute("SELECT * FROM events WHERE correlation = ? ORDER BY seq", (correlation,)).fetchall()
    return [_row_to_event(r) for r in rows]


class ChainReport(BaseModel):
    ok: bool
    checked: int
    first_broken_seq: int | None = None
    head_hash: str | None = None


def verify_chain() -> ChainReport:
    prev: str | None = None
    checked = 0
    with store.reading() as conn:
        for row in conn.execute("SELECT * FROM events ORDER BY seq"):
            event = _row_to_event(row)
            expected = chain_hash(prev, _canonical(event.id, event.ts, event, row["payload"]))
            if event.prev_hash != prev or event.hash != expected:
                return ChainReport(ok=False, checked=checked, first_broken_seq=event.seq, head_hash=prev)
            prev = event.hash
            checked += 1
    return ChainReport(ok=True, checked=checked, head_hash=prev)


def stats(window_s: float = 24 * 3600) -> dict[str, Any]:
    """Per-tool call counts, error rate and p50/p95 latency for the panel's overview."""
    since = time.time() - window_s
    with store.reading() as conn:
        rows = conn.execute(
            "SELECT tool, outcome, duration_ms FROM events WHERE kind = 'tool_call' AND ts >= ?", (since,)
        ).fetchall()
    by_tool: dict[str, list[Any]] = {}
    for r in rows:
        by_tool.setdefault(r["tool"] or "?", []).append(r)
    out = []
    for tool, items in sorted(by_tool.items()):
        durations = sorted(i["duration_ms"] or 0 for i in items)
        errors = sum(1 for i in items if i["outcome"] != "ok")
        out.append({
            "tool": tool, "calls": len(items), "errors": errors,
            "error_rate": round(errors / len(items), 3),
            "p50_ms": durations[len(durations) // 2],
            "p95_ms": durations[min(len(durations) - 1, int(len(durations) * 0.95))],
        })
    return {"window_s": window_s, "total_calls": len(rows), "tools": out}
