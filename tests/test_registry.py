import httpx
import pytest

from gateway import access, catalog, executor, registry, secrets_store
from gateway.errors import InvalidDefinition, PermissionDenied


def defn(**overrides):
    base = {
        "name": "weather.forecast", "title": "Forecast",
        "description": "Daily forecast for a city (example upstream).",
        "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        "http": {"url": "https://api.example.org/v1/forecast/{city}",
                 "headers": {"Authorization": "Bearer {{secret:weather_token}}"}},
    }
    base.update(overrides)
    return registry.DynamicToolDefinition.model_validate(base)


@pytest.fixture
def people():
    access.seed_demo()
    return access.get_principal("analyst"), access.get_principal("admin")


@pytest.mark.parametrize("override, message", [
    ({"name": "Weather"}, "domain.action"),
    ({"name": "invoices.extra"}, "reserved"),
    ({"input_schema": {"type": "array"}}, "type 'object'"),
    ({"input_schema": {"type": "object", "properties": {"x": {"type": "nope"}}}}, "not valid JSON Schema"),
    ({"http": {"url": "http://api.example.org/{city}"}}, "https"),
    ({"http": {"url": "https://169.254.169.254/latest/{city}"}}, "not allowed"),
    ({"http": {"url": "https://10.0.0.8/{city}"}}, "not allowed"),
    ({"http": {"url": "https://api.example.org/{town}"}}, "placeholders"),
    ({"http": {"url": "https://api.example.org/{city}", "headers": {"Authorization": "Bearer abc123abc123abc123"}}},
     "secret:name"),
    ({"http": {"url": "https://api.example.org/{city}", "headers": {"X-Extra": "sk-abcdefghijklmnopqrstu"}}},
     "literal credential"),
])
def test_validation_rejects(people, override, message):
    analyst, _ = people
    with pytest.raises(InvalidDefinition) as exc:
        registry.propose(defn(**override), analyst)
    assert message in exc.value.message


def test_four_eyes(people):
    analyst, admin = people
    rev = registry.propose(defn(), admin)
    with pytest.raises(PermissionDenied):
        registry.review(rev.name, rev.revision, admin, approve=True)  # own tool
    with pytest.raises(PermissionDenied):
        registry.review(rev.name, rev.revision, analyst, approve=True)  # lacks registry.review


def test_draft_is_invisible_until_approved(people):
    analyst, admin = people
    rev = registry.propose(defn(), analyst)
    assert "weather.forecast" not in {t.name for t in catalog.all_tools()}
    registry.review(rev.name, rev.revision, admin, approve=True)
    assert catalog.get("weather.forecast").origin == "dynamic"


def test_new_approval_supersedes_old(people):
    analyst, admin = people
    r1 = registry.propose(defn(), analyst)
    registry.review(r1.name, 1, admin, approve=True)
    r2 = registry.propose(defn(title="Forecast v2"), analyst)
    registry.review(r2.name, 2, admin, approve=True)
    statuses = {r.revision: r.status for r in registry.list_revisions()}
    assert statuses == {1: "superseded", 2: "approved"}
    assert catalog.get("weather.forecast").title == "Forecast v2"


def test_dynamic_call_resolves_caller_secret(people, monkeypatch):
    analyst, admin = people
    rev = registry.propose(defn(), analyst)
    registry.review(rev.name, rev.revision, admin, approve=True)
    secrets_store.put("admin", "weather_token", "tok-admin")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"city": "Porto Lume", "max_c": 31})

    monkeypatch.setattr(registry, "transport", httpx.MockTransport(handler))
    out = executor.execute(admin, "weather.forecast", {"city": "Porto Lume"})
    assert out.ok and out.result["max_c"] == 31
    assert seen["url"].endswith("/forecast/Porto%20Lume")
    assert seen["auth"] == "Bearer tok-admin"


def test_upstream_error_becomes_tool_failed(people, monkeypatch):
    analyst, admin = people
    rev = registry.propose(defn(http={"url": "https://api.example.org/{city}"}), analyst)
    registry.review(rev.name, rev.revision, admin, approve=True)
    monkeypatch.setattr(registry, "transport", httpx.MockTransport(lambda r: httpx.Response(503, text="down")))
    out = executor.execute(admin, "weather.forecast", {"city": "x"})
    assert out.error["error"] == "tool_failed" and out.error["detail"]["status"] == 503


def test_governance_through_tools(people):
    analyst, admin = people
    proposed = executor.execute(analyst, "registry.propose", {"definition": defn().model_dump()})
    assert proposed.ok and proposed.result["status"] == "draft"
    reviewed = executor.execute(admin, "registry.review", {"name": "weather.forecast", "revision": 1, "approve": True})
    assert reviewed.result["status"] == "approved"
