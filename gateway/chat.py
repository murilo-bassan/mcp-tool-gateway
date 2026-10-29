"""Chat over the governed tools.

A message goes through the same pipeline a careful operator would follow:

    route (which tool?) → extract arguments → ask for what is missing → execute → explain

Two engines share that contract:
  * `DeterministicChat` (default, offline): routes with the intent scorer, pulls
    arguments with explicit extractors (tax ids, invoice/agreement ids, states,
    towns, kinds), and explains results with templates in PT-BR or EN.
  * `LLMChat` (when `GATEWAY_LLM_API_KEY` is set): an OpenAI-compatible
    tool-calling loop over the *same* visible tools.

Either way, every tool call goes through `executor.execute` — the chat has no
privilege the user does not have, and every call lands in the audit trail.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

from gateway import catalog, executor, intents
from gateway.access import Principal
from gateway.domains import synthetic

Lang = Literal["pt", "en"]


@dataclass
class Reply:
    text: str
    tool: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: dict[str, Any] | None = None
    pending: dict[str, Any] | None = None       # {"tool", "arguments", "missing"} — the next message fills it
    trace: list[dict[str, Any]] = field(default_factory=list)
    correlation: str | None = None


T = {
    "help": {"pt": "Posso ajudar com notas fiscais (validar CPF/CNPJ, buscar notas, calcular retenções) e convênios "
                   "(buscar, resumo por estado, sinais de risco). Exemplos: “valida o CNPJ 11.222.333/0001-81”, "
                   "“quais convênios estão atrasados em MS?”, “calcula a retenção da NF-100003”.",
             "en": "I can help with invoices (validate CPF/CNPJ, search invoices, compute withholding) and agreements "
                   "(search, totals by state, risk flags). Try “validate CNPJ 11.222.333/0001-81”, "
                   "“which agreements are overdue in MS?”, “compute withholding for NF-100003”."},
    "ask_tax_id": {"pt": "Qual CPF ou CNPJ você quer validar?", "en": "Which CPF or CNPJ should I validate?"},
    "ask_invoice": {"pt": "Qual o número da nota? (ex.: NF-100003)", "en": "Which invoice? (e.g. NF-100003)"},
    "ask_agreement": {"pt": "Qual o convênio? (ex.: AG-2024-1001)", "en": "Which agreement? (e.g. AG-2024-1001)"},
    "denied": {"pt": "Você não tem permissão para usar “{tool}”. Peça acesso a um administrador.",
               "en": "You are not allowed to use “{tool}”. Ask an administrator for access."},
    "failed": {"pt": "A ferramenta “{tool}” falhou: {message}", "en": "The tool “{tool}” failed: {message}"},
}

STATES = set(synthetic.STATES)
_TAX = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b|\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_NF = re.compile(r"\bnf[-\s]?(\d{6})\b", re.I)
_AG = re.compile(r"\bag[-\s]?(\d{4})[-\s]?(\d+)\b", re.I)
_UF = re.compile(r"\b(" + "|".join(sorted(STATES)) + r")\b")


def extract(tool: str, message: str) -> dict[str, Any]:
    """Explicit, testable argument extraction — no guessing beyond what the text says."""
    folded = intents.normalize(message)
    args: dict[str, Any] = {}
    if tool == "invoices.validate_tax_id" and (m := _TAX.search(message)):
        args["tax_id"] = m.group(0)
    if tool in ("invoices.get", "invoices.compute_withholding") and (m := _NF.search(message)):
        args["id"] = f"NF-{m.group(1)}"
    if tool == "grants.get_agreement" and (m := _AG.search(message)):
        args["id"] = f"AG-{m.group(1)}-{m.group(2)}"
    if tool in ("grants.search_agreements", "grants.flag_risks") and (m := _UF.search(message)):
        args["state"] = m.group(1)
    if tool == "grants.search_agreements":
        for town in synthetic.TOWNS:
            if intents.normalize(town) in folded:
                args["town"] = town
        for status, words in {"awaiting_report": ["prestacao", "awaiting"], "completed": ["concluid", "completed"],
                              "cancelled": ["cancelad", "cancelled"], "in_execution": ["em execucao", "in execution"]}.items():
            if any(w in folded for w in words):
                args["status"] = status
    if tool == "invoices.search":
        for kind, words in {"service": ["servico", "service"], "material": ["material"], "hybrid": ["hibrid", "hybrid"]}.items():
            if any(w in folded for w in words):
                args["kind"] = kind
        for word in synthetic.SUPPLIER_WORDS:
            if intents.normalize(word) in folded.split():
                args["supplier"] = word
        args["limit"] = 5
    if tool in ("grants.search_agreements", "grants.flag_risks"):
        args["limit"] = 5
    return args


def _money(v: float, lang: Lang) -> str:
    s = f"{v:,.2f}"
    return "R$ " + (s.replace(",", "X").replace(".", ",").replace("X", ".") if lang == "pt" else s)


_FLAG_WORDS = {
    "pt": {"past_end_date": "prazo vencido", "low_execution": "pouco dinheiro liberado",
           "thin_counterpart": "contrapartida baixa", "late_report": "prestação de contas atrasada"},
    "en": {"past_end_date": "past its end date", "low_execution": "little money released",
           "thin_counterpart": "low local contribution", "late_report": "overdue report"},
}


def explain(tool: str, result: Any, lang: Lang) -> str:
    pt = lang == "pt"
    if tool == "invoices.validate_tax_id":
        kind = result["kind"].upper()
        return (f"O {kind} é {'válido' if result['valid'] else 'inválido'} (dígitos verificadores {'conferem' if result['valid'] else 'não conferem'})."
                if pt else f"The {kind} is {'valid' if result['valid'] else 'invalid'} (check digits {'match' if result['valid'] else 'do not match'}).")
    if tool == "invoices.compute_withholding":
        lines = "; ".join(f"{x['tax']} {x['rate_pct']}% = {_money(x['value'], lang)}" for x in result["lines"])
        return (f"Nota {result['invoice']}: bruto {_money(result['gross_value'], lang)}, retido {_money(result['total_withheld'], lang)} "
                f"({lines}), líquido a pagar {_money(result['net_payable'], lang)}. Tabela ilustrativa, não é orientação fiscal."
                if pt else f"Invoice {result['invoice']}: gross {_money(result['gross_value'], lang)}, withheld "
                f"{_money(result['total_withheld'], lang)} ({lines}), net payable {_money(result['net_payable'], lang)}. Illustrative table, not tax advice.")
    if tool == "invoices.search":
        items = ", ".join(f"{i['id']} ({i['supplier']}, {_money(i['gross_value'], lang)})" for i in result["items"])
        return (f"Encontrei {result['total']} notas. Primeiras: {items}." if pt else f"Found {result['total']} invoices. First ones: {items}.") \
            if result["total"] else ("Nenhuma nota encontrada." if pt else "No invoices found.")
    if tool == "invoices.get":
        return (f"{result['id']}: {result['quantity']}× {result['item']} de {result['supplier']}, {_money(result['gross_value'], lang)}, emitida em {result['issued_on']}."
                if pt else f"{result['id']}: {result['quantity']}× {result['item']} from {result['supplier']}, {_money(result['gross_value'], lang)}, issued {result['issued_on']}.")
    if tool == "grants.flag_risks":
        if not result["flagged"]:
            return "Nenhum convênio com sinal de risco." if pt else "No agreement shows a risk signal."
        flags = _FLAG_WORDS["pt" if pt else "en"]
        top = "; ".join(f"{i['id']} em {i['town']}/{i['state']}: {', '.join(flags.get(f['code'], f['code']) for f in i['flags'])}" if pt else
                        f"{i['id']} in {i['town']}/{i['state']}: {', '.join(flags.get(f['code'], f['code']) for f in i['flags'])}" for i in result["items"][:5])
        return (f"{result['flagged']} convênios com sinais de risco (referência {result['as_of']}). Principais: {top}."
                if pt else f"{result['flagged']} agreements show risk signals (as of {result['as_of']}). Top: {top}.")
    if tool == "grants.search_agreements":
        items = "; ".join(f"{i['id']} {i['town']}/{i['state']} {_money(i['federal_value'], lang)} ({i['status']})" for i in result["items"])
        return (f"{result['total']} convênios encontrados. {items}." if pt else f"{result['total']} agreements found. {items}.") \
            if result["total"] else ("Nenhum convênio encontrado." if pt else "No agreements found.")
    if tool == "grants.summary_by_state":
        rows = sorted(result["states"], key=lambda r: -r["federal_value"])[:5]
        top = "; ".join(f"{r['state']}: {r['count']} · {_money(r['federal_value'], lang)} · {r['disbursement_ratio']:.0%}" for r in rows)
        return (f"Maiores valores por estado (quantidade · valor federal · % desembolsado): {top}."
                if pt else f"Largest totals by state (count · federal value · % disbursed): {top}.")
    if tool == "grants.get_agreement":
        return (f"{result['id']} — {result['program']} em {result['town']}/{result['state']}, {_money(result['federal_value'], lang)}, "
                f"desembolsado {_money(result['disbursed_value'], lang)}, situação {result['status']}."
                if pt else f"{result['id']} — {result['program']} in {result['town']}/{result['state']}, {_money(result['federal_value'], lang)}, "
                f"disbursed {_money(result['disbursed_value'], lang)}, status {result['status']}.")
    return json.dumps(result, ensure_ascii=False)[:600]


class DeterministicChat:
    engine = "deterministic"

    def reply(self, principal: Principal, message: str, lang: Lang = "pt", pending: dict[str, Any] | None = None,
              context: dict[str, Any] | None = None) -> Reply:
        """`context`: the previous successful call in this conversation ({"tool", "arguments"}), for follow-ups
        like "e em GO?" that only change a parameter."""
        correlation = uuid.uuid4().hex[:16]
        visible = [t for t in catalog.visible_to(principal.role.allows_tool) if not t.name.startswith(("meta.", "registry."))]
        trace: list[dict[str, Any]] = []

        if pending:   # the user is answering our follow-up question
            tool = pending["tool"]
            args = {**pending.get("arguments", {}), **extract(tool, message)}
            trace.append({"step": "follow_up", "tool": tool})
        else:
            hits = intents.suggest(message, visible, top_k=3, min_score=1.0)
            trace.append({"step": "route", "candidates": [{"tool": h.tool, "score": h.score, "reasons": list(h.reasons)} for h in hits]})
            if not hits and context and context.get("tool") in {v.name for v in visible}:
                # "e em GO?" — same question as before, one argument changed
                changed = {k: v for k, v in extract(context["tool"], message).items() if k != "limit"}
                if changed:
                    hits = [intents.Suggestion(tool=context["tool"], score=1.0, reasons=("follow-up of previous question",))]
                    trace.append({"step": "context", "tool": context["tool"], "changed": changed})
            if not hits and (_NF.search(message) or _AG.search(message)):
                # an explicit id is enough to know what the user wants to look at
                hits = [intents.Suggestion(tool="invoices.get" if _NF.search(message) else "grants.get_agreement",
                                           score=1.0, reasons=("explicit id",))]
            if not hits:
                return Reply(T["help"][lang], trace=trace, correlation=correlation)
            # Prefer the best-ranked tool whose required arguments the message actually contains;
            # only fall back to asking a follow-up when none of the candidates can run as-is.
            ranked = [h.tool for h in hits]
            if _NF.search(message) and "invoices.search" in ranked and "invoices.compute_withholding" not in ranked:
                ranked.insert(0, "invoices.get")
            if _AG.search(message):
                ranked.insert(0, "grants.get_agreement")
            def runnable(name: str) -> bool:
                required = catalog.get(name).input_schema.get("required", [])
                return all(r in extract(name, message) for r in required)
            tool = next((t for t in ranked if runnable(t) and t in {v.name for v in visible}), ranked[0])
            args = extract(tool, message)

        spec = catalog.get(tool)
        missing = [r for r in spec.input_schema.get("required", []) if r not in args]
        trace.append({"step": "extract", "tool": tool, "arguments": args, "missing": missing})
        if missing:
            key = {"invoices.validate_tax_id": "ask_tax_id", "invoices.get": "ask_invoice",
                   "invoices.compute_withholding": "ask_invoice", "grants.get_agreement": "ask_agreement"}.get(tool, "help")
            return Reply(T[key][lang], tool=tool, arguments=args, trace=trace, correlation=correlation,
                         pending={"tool": tool, "arguments": args, "missing": missing})

        outcome = executor.execute(principal, tool, args, correlation)
        trace.append({"step": "execute", "tool": tool, "ok": outcome.ok, "duration_ms": outcome.duration_ms})
        if not outcome.ok:
            err = outcome.error or {}
            text = (T["denied"][lang].format(tool=tool) if err.get("error") == "permission_denied"
                    else T["failed"][lang].format(tool=tool, message=err.get("message", "")))
            return Reply(text, tool=tool, arguments=args, error=err, trace=trace, correlation=correlation)
        return Reply(explain(tool, outcome.result, lang), tool=tool, arguments=args, result=outcome.result,
                     trace=trace, correlation=correlation)


class LLMChat:
    """OpenAI-compatible tool calling over the caller's visible tools, every call through the executor."""
    engine = "llm"

    def __init__(self, base_url: str, api_key: str, model: str, transport: httpx.BaseTransport | None = None,
                 max_steps: int = 4) -> None:
        self.model, self.max_steps = model, max_steps
        self._http = httpx.Client(base_url=base_url, timeout=60, transport=transport,
                                  headers={"Authorization": f"Bearer {api_key}"})

    @staticmethod
    def _fn(name: str) -> str:   # function names may not contain dots
        return name.replace(".", "__")

    def reply(self, principal: Principal, message: str, lang: Lang = "pt", pending: dict[str, Any] | None = None) -> Reply:
        correlation = uuid.uuid4().hex[:16]
        visible = [t for t in catalog.visible_to(principal.role.allows_tool) if not t.name.startswith("registry.")]
        by_fn = {self._fn(t.name): t.name for t in visible}
        tools = [{"type": "function", "function": {"name": self._fn(t.name), "description": t.description,
                                                   "parameters": t.input_schema}} for t in visible]
        system = ("Você é o assistente do toolgate. Use as ferramentas para responder; nunca invente dados. Responda em português do Brasil."
                  if lang == "pt" else "You are the toolgate assistant. Use the tools to answer; never invent data. Answer in English.")
        messages: list[dict[str, Any]] = [{"role": "system", "content": system}, {"role": "user", "content": message}]
        trace, last_tool, last_args, last_result = [], None, {}, None
        for _ in range(self.max_steps):
            r = self._http.post("/chat/completions", json={"model": self.model, "messages": messages, "tools": tools, "temperature": 0})
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]
            calls = msg.get("tool_calls") or []
            if not calls:
                return Reply(msg.get("content") or "", tool=last_tool, arguments=last_args, result=last_result,
                             trace=trace, correlation=correlation)
            messages.append({"role": "assistant", "content": msg.get("content"), "tool_calls": calls})
            for c in calls:
                name = by_fn.get(c["function"]["name"], c["function"]["name"])
                args = json.loads(c["function"].get("arguments") or "{}")
                out = executor.execute(principal, name, args, correlation)
                trace.append({"step": "tool_call", "tool": name, "arguments": args, "ok": out.ok})
                last_tool, last_args, last_result = name, args, out.result
                messages.append({"role": "tool", "tool_call_id": c["id"],
                                 "content": json.dumps(out.result if out.ok else out.error, ensure_ascii=False, default=str)[:6000]})
        return Reply("…", tool=last_tool, trace=trace, correlation=correlation)


def engine() -> DeterministicChat | LLMChat:
    key = os.environ.get("GATEWAY_LLM_API_KEY")
    if key:
        return LLMChat(os.environ.get("GATEWAY_LLM_BASE_URL", "https://openrouter.ai/api/v1"), key,
                       os.environ.get("GATEWAY_LLM_MODEL", ""))
    return DeterministicChat()
