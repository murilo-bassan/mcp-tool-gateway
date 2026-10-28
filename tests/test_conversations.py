import pytest
from fastapi.testclient import TestClient

from gateway import access, conversations
from gateway.errors import NotFound
from web.app import app

H = {"X-Requested-With": "gateway-panel"}


def client_as(user):
    c = TestClient(app)
    c.__enter__()
    assert c.post("/api/login", json={"user": user, "password": user}, headers=H).status_code == 200
    return c


def test_chat_creates_and_stores_a_conversation():
    c = client_as("analyst")
    r = c.post("/api/chat", json={"message": "valida o CNPJ 11.222.333/0001-81"}, headers=H).json()
    conv_id = r["conversation_id"]
    listed = c.get("/api/conversations").json()
    assert listed[0]["id"] == conv_id and listed[0]["title"] == "valida o CNPJ 11.222.333/0001-81" and listed[0]["messages"] == 2
    full = c.get(f"/api/conversations/{conv_id}").json()
    assert [m["role"] for m in full["messages"]] == ["user", "bot"]
    assert full["messages"][1]["tool"] == "invoices.validate_tax_id" and full["messages"][1]["result"]["valid"] is True


def test_follow_up_survives_across_requests():
    c = client_as("analyst")
    first = c.post("/api/chat", json={"message": "valida um cpf pra mim"}, headers=H).json()
    conv_id = first["conversation_id"]
    assert c.get("/api/conversations").json()[0]["pending"]["tool"] == "invoices.validate_tax_id"
    # a new client session (another tab / another day) answers the pending question
    later = client_as("analyst")
    second = later.post("/api/chat", json={"message": "529.982.247-25", "conversation_id": conv_id}, headers=H).json()
    assert second["result"] == {"kind": "cpf", "valid": True}
    assert later.get(f"/api/conversations/{conv_id}").json()["pending"] is None
    assert len(later.get(f"/api/conversations/{conv_id}").json()["messages"]) == 4


def test_conversations_are_private():
    owner = client_as("analyst")
    conv_id = owner.post("/api/chat", json={"message": "resumo dos convênios por estado"}, headers=H).json()["conversation_id"]
    other = client_as("admin")
    assert other.get(f"/api/conversations/{conv_id}").status_code == 404
    assert other.post("/api/chat", json={"message": "oi", "conversation_id": conv_id}, headers=H).status_code == 404
    assert other.delete(f"/api/conversations/{conv_id}", headers=H).status_code == 404
    assert all(c["id"] != conv_id for c in other.get("/api/conversations").json())


def test_rename_delete_and_order():
    c = client_as("analyst")
    a = c.post("/api/chat", json={"message": "primeira"}, headers=H).json()["conversation_id"]
    b = c.post("/api/chat", json={"message": "segunda"}, headers=H).json()["conversation_id"]
    assert [x["id"] for x in c.get("/api/conversations").json()][:2] == [b, a]
    c.post("/api/chat", json={"message": "de novo", "conversation_id": a}, headers=H)
    assert c.get("/api/conversations").json()[0]["id"] == a          # most recent activity first
    assert c.patch(f"/api/conversations/{a}", json={"title": "Convênios MS"}, headers=H).json()["title"] == "Convênios MS"
    c.delete(f"/api/conversations/{a}", headers=H)
    assert c.get(f"/api/conversations/{a}").status_code == 404


def test_module_ownership_and_long_titles():
    access.seed_demo()
    conv = conversations.create("analyst", "x" * 300, "pt")
    assert len(conv["title"]) == conversations.TITLE_MAX and conv["title"].endswith("…")
    with pytest.raises(NotFound):
        conversations.messages("admin", conv["id"])


def test_follow_up_reuses_the_previous_tool():
    c = client_as("analyst")
    first = c.post("/api/chat", json={"message": "quais convênios estão atrasados em MS?"}, headers=H).json()
    second = c.post("/api/chat", json={"message": "e em GO?", "conversation_id": first["conversation_id"]}, headers=H).json()
    assert second["tool"] == "grants.flag_risks" and second["arguments"]["state"] == "GO"
    assert all(i["state"] == "GO" for i in second["result"]["items"])
    fresh = c.post("/api/chat", json={"message": "e em GO?"}, headers=H).json()      # no history → no guess
    assert fresh["tool"] is None
