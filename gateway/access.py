"""Who is calling, and what they may call.

Two kinds of principal share one table:
  * `user`     — a person in the panel; logs in with a password, gets a session token.
  * `consumer` — a service (another backend, a bot); sends an API key on every call.

Permission is decided by the principal's *role*: a list of fnmatch globs over
tool names (`invoices.*`, `grants.search_*`, `*`) plus a short list of
administrative permissions (`registry.write`, `registry.review`, `audit.read`,
`secrets.write`, `access.admin`). Roles live in the database, not in code, so
granting access is an operation, not a deploy (docs/adr/0003-roles-as-data.md).

Passwords and API keys are never stored: users get scrypt with a per-user
salt, consumer keys (high-entropy already) get a plain SHA-256.
"""
from __future__ import annotations

import fnmatch
import hashlib
import hmac
import json
import secrets
import time
from typing import Literal

from pydantic import BaseModel

from gateway import store
from gateway.config import get_settings
from gateway.errors import AuthFailed, NotFound, PermissionDenied

AdminPerm = Literal["registry.write", "registry.review", "audit.read", "secrets.write", "access.admin"]
ADMIN_PERMS: tuple[str, ...] = ("registry.write", "registry.review", "audit.read", "secrets.write", "access.admin")


class Role(BaseModel):
    name: str
    description: str = ""
    tool_globs: list[str] = []
    admin_perms: list[str] = []

    def allows_tool(self, tool_name: str) -> bool:
        return any(fnmatch.fnmatchcase(tool_name, glob) for glob in self.tool_globs)


class Principal(BaseModel):
    id: str
    kind: Literal["user", "consumer"]
    display_name: str
    role: Role
    status: Literal["active", "blocked"] = "active"

    def can(self, perm: str) -> bool:
        return perm in self.role.admin_perms

    def require(self, perm: str) -> None:
        if not self.can(perm):
            raise PermissionDenied(f"'{self.id}' lacks '{perm}'", detail={"permission": perm})


# ---------------------------------------------------------------- hashing

def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    candidate = hash_password(password, bytes.fromhex(salt_hex)).split("$")[2]
    return hmac.compare_digest(candidate, digest_hex)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# ---------------------------------------------------------------- roles

def upsert_role(role: Role) -> Role:
    unknown = set(role.admin_perms) - set(ADMIN_PERMS)
    if unknown:
        raise ValueError(f"unknown admin permissions: {sorted(unknown)}")
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO roles (name, description, tool_globs, admin_perms) VALUES (?, ?, ?, ?)"
            " ON CONFLICT(name) DO UPDATE SET description = excluded.description,"
            " tool_globs = excluded.tool_globs, admin_perms = excluded.admin_perms",
            (role.name, role.description, json.dumps(role.tool_globs), json.dumps(role.admin_perms)),
        )
    return role


def get_role(name: str) -> Role:
    with store.reading() as conn:
        row = conn.execute("SELECT * FROM roles WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise NotFound(f"role '{name}' not found")
    return Role(name=row["name"], description=row["description"],
                tool_globs=json.loads(row["tool_globs"]), admin_perms=json.loads(row["admin_perms"]))


def list_roles() -> list[Role]:
    with store.reading() as conn:
        names = [r["name"] for r in conn.execute("SELECT name FROM roles ORDER BY name")]
    return [get_role(n) for n in names]


# ---------------------------------------------------------------- principals

def create_user(user_id: str, password: str, role: str, display_name: str | None = None) -> Principal:
    get_role(role)
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO principals (id, kind, display_name, role, password_hash, created_at)"
            " VALUES (?, 'user', ?, ?, ?, ?)",
            (user_id, display_name or user_id, role, hash_password(password), time.time()),
        )
    return get_principal(user_id)


def create_consumer(consumer_id: str, role: str, display_name: str | None = None) -> tuple[Principal, str]:
    """Creates a service principal. The API key is returned once and never again."""
    get_role(role)
    api_key = "gw_" + secrets.token_urlsafe(32)
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO principals (id, kind, display_name, role, api_key_hash, created_at)"
            " VALUES (?, 'consumer', ?, ?, ?, ?)",
            (consumer_id, display_name or consumer_id, role, _sha256(api_key), time.time()),
        )
    return get_principal(consumer_id), api_key


def get_principal(principal_id: str) -> Principal:
    with store.reading() as conn:
        row = conn.execute("SELECT * FROM principals WHERE id = ?", (principal_id,)).fetchone()
    if row is None:
        raise NotFound(f"principal '{principal_id}' not found")
    return Principal(id=row["id"], kind=row["kind"], display_name=row["display_name"],
                     role=get_role(row["role"]), status=row["status"])


def list_principals() -> list[Principal]:
    with store.reading() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM principals ORDER BY kind, id")]
    return [get_principal(i) for i in ids]


def set_status(principal_id: str, status: Literal["active", "blocked"]) -> None:
    with store.transaction() as conn:
        updated = conn.execute("UPDATE principals SET status = ? WHERE id = ?", (status, principal_id)).rowcount
        if status == "blocked":
            conn.execute("DELETE FROM sessions WHERE principal = ?", (principal_id,))
    if not updated:
        raise NotFound(f"principal '{principal_id}' not found")


def assign_role(principal_id: str, role: str) -> None:
    get_role(role)
    with store.transaction() as conn:
        if not conn.execute("UPDATE principals SET role = ? WHERE id = ?", (role, principal_id)).rowcount:
            raise NotFound(f"principal '{principal_id}' not found")


# ---------------------------------------------------------------- authentication

def _active(principal: Principal) -> Principal:
    if principal.status != "active":
        raise AuthFailed("principal is blocked")
    return principal


def login(user_id: str, password: str) -> str:
    """Checks a password and opens a session. Same error for unknown user and wrong password."""
    with store.reading() as conn:
        row = conn.execute("SELECT password_hash FROM principals WHERE id = ? AND kind = 'user'",
                           (user_id,)).fetchone()
    if row is None or not verify_password(password, row["password_hash"] or ""):
        raise AuthFailed("invalid credentials")
    _active(get_principal(user_id))
    token = secrets.token_urlsafe(32)
    with store.transaction() as conn:
        conn.execute("INSERT INTO sessions (token_hash, principal, expires_at) VALUES (?, ?, ?)",
                     (_sha256(token), user_id, time.time() + get_settings().session_ttl_s))
    return token


def logout(token: str) -> None:
    with store.transaction() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_sha256(token),))


def from_session(token: str) -> Principal:
    with store.reading() as conn:
        row = conn.execute("SELECT principal, expires_at FROM sessions WHERE token_hash = ?",
                           (_sha256(token),)).fetchone()
    if row is None or row["expires_at"] < time.time():
        raise AuthFailed("session expired or unknown")
    return _active(get_principal(row["principal"]))


def from_api_key(api_key: str) -> Principal:
    with store.reading() as conn:
        row = conn.execute("SELECT id FROM principals WHERE api_key_hash = ? AND kind = 'consumer'",
                           (_sha256(api_key),)).fetchone()
    if row is None:
        raise AuthFailed("invalid API key")
    return _active(get_principal(row["id"]))


# ---------------------------------------------------------------- demo seed

DEMO_ROLES = [
    Role(name="admin", description="Everything, including governance.", tool_globs=["*"], admin_perms=list(ADMIN_PERMS)),
    Role(name="analyst", description="Reads every domain; proposes new tools.",
         tool_globs=["invoices.*", "grants.*", "meta.*"], admin_perms=["registry.write"]),
    Role(name="auditor", description="Reads the trail; calls nothing.", tool_globs=["meta.*"], admin_perms=["audit.read"]),
    Role(name="grants-bot", description="Service account for the grants domain only.", tool_globs=["grants.*"]),
]


def seed_demo() -> None:
    """Creates demo roles and users if the store is empty. Idempotent."""
    with store.reading() as conn:
        if conn.execute("SELECT COUNT(*) FROM principals").fetchone()[0]:
            return
    for role in DEMO_ROLES:
        upsert_role(role)
    create_user("admin", "admin", "admin", "Admin (demo)")
    create_user("analyst", "analyst", "analyst", "Analyst (demo)")
    create_user("auditor", "auditor", "auditor", "Auditor (demo)")
