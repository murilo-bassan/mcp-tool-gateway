import pytest

from gateway import secrets_store, store
from gateway.errors import NotFound, RateLimited
from gateway.ratelimit import SlidingWindow


def test_secret_is_encrypted_at_rest():
    secrets_store.put("ana", "weather_token", "plain-value-123")
    with store.reading() as conn:
        raw = conn.execute("SELECT ciphertext FROM secrets").fetchone()["ciphertext"]
    assert b"plain-value-123" not in raw
    assert secrets_store.get("ana", "weather_token") == "plain-value-123"


def test_render_prefers_owner_then_system():
    secrets_store.put(secrets_store.SYSTEM_OWNER, "tok", "shared")
    assert secrets_store.render("Bearer {{secret:tok}}", "bob") == "Bearer shared"
    secrets_store.put("bob", "tok", "mine")
    assert secrets_store.render("Bearer {{secret:tok}}", "bob") == "Bearer mine"


def test_missing_secret_raises():
    with pytest.raises(NotFound):
        secrets_store.render("{{secret:nope}}", "ana")


def test_names_never_values():
    secrets_store.put("ana", "a", "1")
    secrets_store.put("ana", "b", "2")
    assert secrets_store.names("ana") == ["a", "b"]


def test_references():
    assert secrets_store.references("x {{secret:a_1}} {{secret:b}}") == {"a_1", "b"}


def test_sliding_window():
    now = [0.0]
    window = SlidingWindow(limit=2, window_s=60, clock=lambda: now[0])
    window.check("p")
    window.check("p")
    with pytest.raises(RateLimited) as exc:
        window.check("p")
    assert exc.value.detail["retry_after_s"] == 60
    window.check("other")          # per key
    now[0] = 61
    window.check("p")              # window slid
