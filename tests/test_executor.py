import pytest

from gateway import access, audit, executor


@pytest.fixture
def analyst():
    access.seed_demo()
    return access.get_principal("analyst")


def test_ok_call_is_audited(analyst):
    out = executor.execute(analyst, "invoices.validate_tax_id", {"tax_id": "11.222.333/0001-81"})
    assert out.ok and out.result == {"kind": "cnpj", "valid": True}
    event = audit.search(kind="tool_call")[0]
    assert event.actor == "analyst" and event.outcome == "ok" and event.correlation == out.correlation


def test_denied_call_is_audited_too(analyst):
    out = executor.execute(analyst, "registry.review", {"name": "x.y", "revision": 1, "approve": True})
    assert not out.ok and out.error["error"] == "permission_denied"
    assert audit.search(kind="tool_call")[0].outcome == "permission_denied"


def test_schema_errors_have_paths(analyst):
    out = executor.execute(analyst, "grants.search_agreements", {"limit": 500, "bogus": 1})
    assert out.error["error"] == "invalid_arguments"
    paths = {e["path"] for e in out.error["detail"]["errors"]}
    assert "/limit" in paths and "/" in paths  # additionalProperties is reported at the root


def test_unknown_tool(analyst):
    assert executor.execute(analyst, "nope.nothing").error["error"] == "not_found"


def test_defaults_applied(analyst):
    out = executor.execute(analyst, "invoices.search", {})
    assert len(out.result["items"]) == 20


def test_handler_crash_does_not_leak(analyst, monkeypatch):
    import dataclasses

    from gateway import catalog
    spec = catalog.get("invoices.get")
    broken = dataclasses.replace(spec, handler=lambda a, c: 1 / 0)
    monkeypatch.setitem(catalog._NATIVE, "invoices.get", broken)
    out = executor.execute(analyst, "invoices.get", {"id": "NF-100001"})
    assert out.error == {"error": "tool_failed", "message": "internal error in tool: ZeroDivisionError"}


def test_rate_limit(analyst, isolated_settings):
    from gateway import config
    config.override(isolated_settings.model_copy(update={"rate_limit_per_min": 2}))
    executor._limiter.cache_clear()
    results = [executor.execute(analyst, "meta.whoami").ok for _ in range(3)]
    assert results == [True, True, False]
    executor._limiter.cache_clear()
