import pytest
from fastapi.testclient import TestClient

from web.app import app

CSRF = {"X-Requested-With": "gateway-panel"}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def login(client, user="admin"):
    r = client.post("/api/login", json={"user": user, "password": user}, headers=CSRF)
    assert r.status_code == 200, r.text
    return r


def test_login_sets_httponly_cookie(client):
    r = login(client)
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert client.get("/api/me").json()["role"] == "admin"


def test_bad_login_is_401_and_audited(client):
    r = client.post("/api/login", json={"user": "admin", "password": "x"}, headers=CSRF)
    assert r.status_code == 401
    login(client)
    events = client.get("/api/audit?kind=login").json()
    assert [e["outcome"] for e in events][:2] == ["ok", "failed"]


def test_mutation_without_csrf_header_is_refused(client):
    login(client)
    r = client.post("/api/call", json={"tool": "meta.whoami"})
    assert r.status_code == 403


def test_call_through_panel(client):
    login(client, "analyst")
    r = client.post("/api/call", json={"tool": "grants.flag_risks", "arguments": {"state": "MS"}}, headers=CSRF)
    body = r.json()
    assert body["ok"] and body["result"]["as_of"] == "2026-10-01"


def test_tools_are_filtered(client):
    login(client, "auditor")
    assert {t["domain"] for t in client.get("/api/tools").json()} == {"meta"}


def test_audit_requires_permission_for_others(client):
    login(client, "analyst")
    client.post("/api/call", json={"tool": "meta.whoami"}, headers=CSRF)
    rows = client.get("/api/audit").json()
    assert rows and {r["actor"] for r in rows} == {"analyst"}
    assert client.get("/api/audit/verify").status_code == 403


def test_audit_by_correlation_is_one_request_and_still_scoped(client):
    login(client, "auditor")
    corr = client.post("/api/call", json={"tool": "meta.whoami"}, headers=CSRF).json()["correlation"]
    client.post("/api/call", json={"tool": "meta.whoami"}, headers=CSRF)
    rows = client.get(f"/api/audit?correlation={corr}").json()
    assert rows and {r["correlation"] for r in rows} == {corr}
    login(client, "analyst")  # someone else's request is invisible without audit.read
    assert client.get(f"/api/audit?correlation={corr}").json() == []


def test_consumer_flow(client):
    login(client)
    created = client.post("/api/access/consumers", json={"id": "grants-sync", "role": "grants-bot"}, headers=CSRF).json()
    with TestClient(app) as service:
        ok = service.post("/v1/call", json={"tool": "grants.summary_by_state"}, headers={"X-API-Key": created["api_key"]})
        denied = service.post("/v1/call", json={"tool": "invoices.search"}, headers={"X-API-Key": created["api_key"]})
        anon = service.post("/v1/call", json={"tool": "invoices.search"}, headers={"X-API-Key": "gw_wrong"})
    assert ok.json()["ok"] is True
    assert denied.json()["error"]["error"] == "permission_denied"
    assert anon.status_code == 401


def test_secrets_never_returned(client):
    login(client)
    client.put("/api/secrets", json={"name": "weather_token", "value": "s3cr3t-value"}, headers=CSRF)
    listing = client.get("/api/secrets").json()
    assert listing["mine"] == ["weather_token"]
    assert "s3cr3t-value" not in client.get("/api/audit?kind=secret").text


def test_security_headers(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
