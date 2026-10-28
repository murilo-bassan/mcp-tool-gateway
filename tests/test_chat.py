import json

import httpx
import pytest
from fastapi.testclient import TestClient

from gateway import access, audit, chat
from web.app import app


@pytest.fixture
def analyst():
    access.seed_demo()
    return access.get_principal("analyst")


@pytest.mark.parametrize("message, tool", [
    ("valida o CNPJ 11.222.333/0001-81", "invoices.validate_tax_id"),
    ("quais convênios estão atrasados em MS?", "grants.flag_risks"),
    ("which agreements are overdue in GO?", "grants.flag_risks"),
    ("calcula a retenção da NF-100003", "invoices.compute_withholding"),
    ("resumo dos convênios por estado", "grants.summary_by_state"),
    ("me mostra o convênio AG-2024-1001", "grants.get_agreement"),
    ("detalhe da NF-100010", "invoices.get"),
    ("convênios de Porto Lume", "grants.search_agreements"),
])
def test_routes_and_executes(analyst, message, tool):
    r = chat.DeterministicChat().reply(analyst, message, "pt")
    assert r.tool == tool and r.result is not None and r.error is None


def test_arguments_are_extracted_not_guessed(analyst):
    r = chat.DeterministicChat().reply(analyst, "quais convênios estão atrasados em MS?", "pt")
    assert r.arguments == {"state": "MS", "limit": 5}
    assert all(i["state"] == "MS" for i in r.result["items"])


def test_follow_up_question_then_answer(analyst):
    bot = chat.DeterministicChat()
    first = bot.reply(analyst, "valida um cpf pra mim", "pt")
    assert first.pending == {"tool": "invoices.validate_tax_id", "arguments": {}, "missing": ["tax_id"]}
    assert first.text.startswith("Qual CPF")
    second = bot.reply(analyst, "529.982.247-25", "pt", first.pending)
    assert "válido" in second.text and second.result == {"kind": "cpf", "valid": True}


def test_languages(analyst):
    bot = chat.DeterministicChat()
    assert "válido" in bot.reply(analyst, "valida o CNPJ 11.222.333/0001-81", "pt").text
    assert "valid" in bot.reply(analyst, "validate CNPJ 11.222.333/0001-81", "en").text
    assert bot.reply(analyst, "qual a previsão do tempo?", "pt").text.startswith("Posso ajudar")


def test_chat_respects_permissions_and_audits():
    access.seed_demo()
    auditor = access.get_principal("auditor")
    r = chat.DeterministicChat().reply(auditor, "valida o CNPJ 11.222.333/0001-81", "pt")
    assert r.tool is None                       # the auditor's role sees no business tools to route to
    analyst = access.get_principal("analyst")
    r = chat.DeterministicChat().reply(analyst, "valida o CNPJ 11.222.333/0001-81", "pt")
    assert audit.correlated(r.correlation)[0].tool == "invoices.validate_tax_id"


def test_llm_chat_tool_calling_loop(analyst):
    turns = []

    def handler(request):
        body = json.loads(request.content)
        turns.append(body)
        if len(turns) == 1:
            assert any(t["function"]["name"] == "invoices__validate_tax_id" for t in body["tools"])
            return httpx.Response(200, json={"choices": [{"message": {"content": None, "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "invoices__validate_tax_id",
                                                              "arguments": json.dumps({"tax_id": "529.982.247-25"})}}]}}]})
        assert json.loads(body["messages"][-1]["content"]) == {"kind": "cpf", "valid": True}
        return httpx.Response(200, json={"choices": [{"message": {"content": "O CPF é válido."}}]})

    bot = chat.LLMChat("https://llm.example", "k", "m", transport=httpx.MockTransport(handler))
    r = bot.reply(analyst, "o cpf 529.982.247-25 é válido?", "pt")
    assert r.text == "O CPF é válido." and r.tool == "invoices.validate_tax_id" and len(turns) == 2


def test_chat_endpoint():
    with TestClient(app) as c:
        c.post("/api/login", json={"user": "analyst", "password": "analyst"}, headers={"X-Requested-With": "gateway-panel"})
        r = c.post("/api/chat", json={"message": "resumo dos convênios por estado", "lang": "pt"},
                   headers={"X-Requested-With": "gateway-panel"})
        body = r.json()
        assert r.status_code == 200 and body["engine"] == "deterministic" and body["tool"] == "grants.summary_by_state"
        assert c.post("/api/chat", json={"message": "oi"}).status_code == 403   # CSRF header required
