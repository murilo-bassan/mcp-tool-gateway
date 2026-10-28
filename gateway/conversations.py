"""Stored chat conversations, so a user can come back to any of them.

Every read and write is scoped to the owner: asking for someone else's
conversation id is answered exactly like asking for one that does not exist
(`NotFound`), so ids cannot be probed. Messages keep the full reply (tool,
arguments, result, trace, correlation) so a reopened conversation shows the
same evidence it showed live, and the correlation id still leads to the audit
trail. The pending follow-up ("Qual CPF?") is stored on the conversation, so it
can be answered later from any device.

Message text is stored as typed: the user needs to read their own history.
The audit trail, which other people read, stays masked.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from gateway import store
from gateway.errors import NotFound

TITLE_MAX = 80


def _title(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= TITLE_MAX else text[: TITLE_MAX - 1].rstrip() + "…"


def create(owner: str, first_message: str, lang: str) -> dict[str, Any]:
    now = time.time()
    conv_id = uuid.uuid4().hex
    with store.transaction() as conn:
        conn.execute("INSERT INTO conversations (id, owner, title, lang, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                     (conv_id, owner, _title(first_message), lang, now, now))
    return get(owner, conv_id)


def _row(row: Any) -> dict[str, Any]:
    return {"id": row["id"], "title": row["title"], "lang": row["lang"],
            "pending": json.loads(row["pending"]) if row["pending"] else None,
            "created_at": row["created_at"], "updated_at": row["updated_at"]}


def get(owner: str, conv_id: str) -> dict[str, Any]:
    with store.reading() as conn:
        row = conn.execute("SELECT * FROM conversations WHERE id = ? AND owner = ?", (conv_id, owner)).fetchone()
    if row is None:
        raise NotFound("conversation not found")
    return _row(row)


def list_for(owner: str, limit: int = 100) -> list[dict[str, Any]]:
    with store.reading() as conn:
        rows = conn.execute(
            """SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS n
               FROM conversations c WHERE owner = ? ORDER BY updated_at DESC LIMIT ?""", (owner, limit)).fetchall()
    return [{**_row(r), "messages": r["n"]} for r in rows]


def messages(owner: str, conv_id: str) -> list[dict[str, Any]]:
    get(owner, conv_id)   # ownership check
    with store.reading() as conn:
        rows = conn.execute("SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY seq",
                            (conv_id,)).fetchall()
    return [{"role": r["role"], **json.loads(r["content"]), "at": r["created_at"]} for r in rows]


def append(owner: str, conv_id: str, user_text: str, reply: dict[str, Any]) -> None:
    """Stores one exchange and the conversation's new pending state, atomically."""
    get(owner, conv_id)
    now = time.time()
    with store.transaction() as conn:
        conn.execute("INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, 'user', ?, ?)",
                     (conv_id, json.dumps({"text": user_text}, ensure_ascii=False), now))
        conn.execute("INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, 'bot', ?, ?)",
                     (conv_id, json.dumps(reply, ensure_ascii=False, default=str), now))
        conn.execute("UPDATE conversations SET updated_at = ?, pending = ? WHERE id = ?",
                     (now, json.dumps(reply["pending"]) if reply.get("pending") else None, conv_id))


def rename(owner: str, conv_id: str, title: str) -> dict[str, Any]:
    get(owner, conv_id)
    with store.transaction() as conn:
        conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (_title(title), conv_id))
    return get(owner, conv_id)


def delete(owner: str, conv_id: str) -> None:
    get(owner, conv_id)
    with store.transaction() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))


def last_call(owner: str, conv_id: str) -> dict[str, Any] | None:
    """The most recent successful tool call in the conversation, used as context for follow-ups."""
    for m in reversed(messages(owner, conv_id)):
        if m["role"] == "bot" and m.get("tool") and m.get("result") is not None:
            return {"tool": m["tool"], "arguments": m.get("arguments") or {}}
    return None
