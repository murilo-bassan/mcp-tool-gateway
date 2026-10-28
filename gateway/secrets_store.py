"""Owner-scoped secrets, encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256).

A dynamic HTTP tool never contains a credential. Its definition references one
by name — `{{secret:weather_token}}` — and the executor resolves it at call
time from the *caller's* secrets first, then the shared `__system__` owner.
So two analysts can use the same tool with their own keys, and a secret's
plaintext never reaches the catalog, the audit trail, or the LLM.
"""
from __future__ import annotations

import re
import time

from cryptography.fernet import Fernet, InvalidToken

from gateway import store
from gateway.config import get_settings
from gateway.errors import GatewayError, NotFound

SYSTEM_OWNER = "__system__"
_REF = re.compile(r"\{\{secret:([a-z0-9_]{1,64})\}\}")
_NAME = re.compile(r"^[a-z0-9_]{1,64}$")


def _fernet() -> Fernet:
    settings = get_settings()
    if settings.secret_key:
        return Fernet(settings.secret_key.encode())
    key_file = settings.data_dir / "secret.key"   # demo fallback; production sets GATEWAY_SECRET_KEY
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    if not key_file.exists():
        key_file.write_bytes(Fernet.generate_key())
    return Fernet(key_file.read_bytes())


def put(owner: str, name: str, value: str) -> None:
    if not _NAME.match(name):
        raise ValueError("secret names are lowercase letters, digits and underscores")
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO secrets (owner, name, ciphertext, updated_at) VALUES (?, ?, ?, ?)"
            " ON CONFLICT(owner, name) DO UPDATE SET ciphertext = excluded.ciphertext, updated_at = excluded.updated_at",
            (owner, name, _fernet().encrypt(value.encode()), time.time()),
        )


def get(owner: str, name: str) -> str:
    with store.reading() as conn:
        row = conn.execute("SELECT ciphertext FROM secrets WHERE owner = ? AND name = ?", (owner, name)).fetchone()
    if row is None:
        raise NotFound(f"secret '{name}' not found")
    try:
        return _fernet().decrypt(row["ciphertext"]).decode()
    except InvalidToken as error:  # key rotated without re-encrypting
        raise GatewayError("secret cannot be decrypted with the current key") from error


def delete(owner: str, name: str) -> None:
    with store.transaction() as conn:
        conn.execute("DELETE FROM secrets WHERE owner = ? AND name = ?", (owner, name))


def names(owner: str) -> list[str]:
    """Names only — the panel lists secrets but never shows a value back."""
    with store.reading() as conn:
        return [r["name"] for r in conn.execute("SELECT name FROM secrets WHERE owner = ? ORDER BY name", (owner,))]


def references(text: str) -> set[str]:
    return set(_REF.findall(text))


def resolve(owner: str, name: str) -> str:
    try:
        return get(owner, name)
    except NotFound:
        return get(SYSTEM_OWNER, name)


def render(template: str, owner: str) -> str:
    """Replaces every `{{secret:name}}` in `template` with its plaintext for `owner`."""
    return _REF.sub(lambda m: resolve(owner, m.group(1)), template)
