"""SQLite storage shared by every module.

One file, WAL mode, schema created idempotently. SQLite keeps the demo
zero-infra; the repository layer is narrow enough to move to Postgres
(see docs/adr/0002-sqlite-first.md and the durable-agent-runtime repo, which
does exactly that for its queue).
"""
from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from gateway.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS roles (
    name         TEXT PRIMARY KEY,
    description  TEXT NOT NULL DEFAULT '',
    tool_globs   TEXT NOT NULL DEFAULT '[]',   -- JSON list of fnmatch patterns
    admin_perms  TEXT NOT NULL DEFAULT '[]'    -- JSON list: registry.write, audit.read, ...
);

CREATE TABLE IF NOT EXISTS principals (
    id            TEXT PRIMARY KEY,
    kind          TEXT NOT NULL CHECK (kind IN ('user', 'consumer')),
    display_name  TEXT NOT NULL,
    role          TEXT NOT NULL REFERENCES roles(name),
    password_hash TEXT,           -- users
    api_key_hash  TEXT,           -- consumers (services)
    status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked')),
    created_at    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash  TEXT PRIMARY KEY,
    principal   TEXT NOT NULL REFERENCES principals(id),
    expires_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS secrets (
    owner       TEXT NOT NULL,
    name        TEXT NOT NULL,
    ciphertext  BLOB NOT NULL,
    updated_at  REAL NOT NULL,
    PRIMARY KEY (owner, name)
);

CREATE TABLE IF NOT EXISTS tool_definitions (
    name         TEXT NOT NULL,
    revision     INTEGER NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('draft', 'approved', 'disabled', 'superseded')),
    definition   TEXT NOT NULL,   -- JSON (DynamicToolDefinition)
    author       TEXT NOT NULL,
    reviewer     TEXT,
    created_at   REAL NOT NULL,
    reviewed_at  REAL,
    PRIMARY KEY (name, revision)
);

CREATE TABLE IF NOT EXISTS events (
    seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    id           TEXT NOT NULL UNIQUE,
    ts           REAL NOT NULL,
    kind         TEXT NOT NULL,
    actor        TEXT,
    tool         TEXT,
    outcome      TEXT,
    duration_ms  INTEGER,
    correlation  TEXT,
    payload      TEXT NOT NULL,   -- JSON, already masked
    prev_hash    TEXT,
    hash         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_kind_ts ON events(kind, ts);
CREATE INDEX IF NOT EXISTS events_correlation ON events(correlation);
"""

_lock = threading.RLock()
_initialized: set[str] = set()


def connect() -> sqlite3.Connection:
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    path = str(settings.db_path)
    conn = sqlite3.connect(path, timeout=10, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    with _lock:
        if path not in _initialized:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA)
            _initialized.add(path)
    return conn


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """`BEGIN IMMEDIATE` so concurrent writers serialize instead of failing mid-way."""
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


@contextmanager
def reading() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def reset_cache() -> None:
    """Forget which files were initialized (tests point at a fresh dir each time)."""
    with _lock:
        _initialized.clear()
