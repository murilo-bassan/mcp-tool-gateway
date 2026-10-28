"""Invoices domain: tax-ID validation, search and illustrative withholding rules.

The withholding rates below are *illustrative* — a fixed, simplified table to
show how deterministic business rules sit next to LLM tools. They are not
tax advice and do not track any real legislation.
"""
from __future__ import annotations

import re
from typing import Any

from gateway.catalog import CallContext, native, object_schema
from gateway.domains import synthetic
from gateway.errors import InvalidArguments, NotFound


def _dv(nums: list[int], weights: list[int]) -> int:
    r = sum(n * w for n, w in zip(nums, weights)) % 11
    return 0 if r < 2 else 11 - r


def validate_cpf(digits: str) -> bool:
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    n = [int(c) for c in digits]
    d1 = (sum(a * b for a, b in zip(n[:9], range(10, 1, -1))) * 10) % 11 % 10
    d2 = (sum(a * b for a, b in zip(n[:10], range(11, 1, -1))) * 10) % 11 % 10
    return n[9] == d1 and n[10] == d2


def validate_cnpj(digits: str) -> bool:
    if len(digits) != 14 or len(set(digits)) == 1:
        return False
    n = [int(c) for c in digits]
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return n[12] == _dv(n[:12], w1) and n[13] == _dv(n[:13], [6] + w1)


@native("invoices.validate_tax_id", title="Validate a CPF/CNPJ",
        description="Checks the check digits of a Brazilian CPF (11 digits) or CNPJ (14 digits). Offline, no lookup.",
        schema=object_schema({"tax_id": {"type": "string", "minLength": 11, "maxLength": 18}}, ["tax_id"]),
        keywords=("cpf", "cnpj", "validar", "documento", "digito verificador", "tax id"))
def validate_tax_id(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    digits = re.sub(r"\D", "", args["tax_id"])
    if len(digits) == 11:
        return {"kind": "cpf", "valid": validate_cpf(digits)}
    if len(digits) == 14:
        return {"kind": "cnpj", "valid": validate_cnpj(digits)}
    raise InvalidArguments("a CPF has 11 digits and a CNPJ 14", detail={"digits": len(digits)})


@native("invoices.search", title="Search invoices",
        description="Searches the synthetic invoice dataset by supplier, item, kind (material/service/hybrid) and date range.",
        schema=object_schema({
            "supplier": {"type": "string"}, "item": {"type": "string"},
            "kind": {"enum": ["material", "service", "hybrid"]},
            "issued_from": {"type": "string", "format": "date"}, "issued_to": {"type": "string", "format": "date"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
        }),
        keywords=("nota fiscal", "notas", "fornecedor", "buscar notas", "invoice"))
def search(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    rows = synthetic.invoices()
    if s := args.get("supplier"):
        rows = [r for r in rows if s.lower() in r["supplier"].lower()]
    if it := args.get("item"):
        rows = [r for r in rows if it.lower() in r["item"].lower()]
    if k := args.get("kind"):
        rows = [r for r in rows if r["kind"] == k]
    if f := args.get("issued_from"):
        rows = [r for r in rows if r["issued_on"] >= f]
    if t := args.get("issued_to"):
        rows = [r for r in rows if r["issued_on"] <= t]
    limit = args.get("limit", 20)
    return {"total": len(rows), "items": rows[:limit]}


@native("invoices.get", title="Get one invoice", description="Returns one synthetic invoice by id (e.g. NF-100007).",
        schema=object_schema({"id": {"type": "string", "pattern": "^NF-\\d+$"}}, ["id"]),
        keywords=("nota", "detalhe da nota", "invoice"))
def get(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    for row in synthetic.invoices():
        if row["id"] == args["id"]:
            return row
    raise NotFound(f"invoice {args['id']} not found")


# Illustrative, simplified table: (income tax %, social contributions %) by kind.
_WITHHOLDING = {"service": (1.5, 4.65), "hybrid": (1.2, 2.0), "material": (0.0, 0.0)}


@native("invoices.compute_withholding", title="Compute withholding (illustrative)",
        description="Applies a fixed, illustrative withholding table to an invoice and explains each line. Deterministic; not tax advice.",
        schema=object_schema({"id": {"type": "string", "pattern": "^NF-\\d+$"}}, ["id"]),
        keywords=("retencao", "imposto", "calcular imposto", "iss", "tributo", "withholding"))
def compute_withholding(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    inv = get(args, ctx)
    gross = inv["gross_value"]
    ir, social = _WITHHOLDING[inv["kind"]]
    lines = [
        {"tax": "ISS", "rate_pct": inv["iss_rate_pct"], "value": round(gross * inv["iss_rate_pct"] / 100, 2),
         "why": f"municipal service tax for '{inv['item']}' ({inv['kind']})"},
        {"tax": "IR", "rate_pct": ir, "value": round(gross * ir / 100, 2), "why": f"income tax rate for kind '{inv['kind']}'"},
        {"tax": "SOCIAL", "rate_pct": social, "value": round(gross * social / 100, 2), "why": "combined social contributions"},
    ]
    withheld = round(sum(line["value"] for line in lines), 2)
    return {"invoice": inv["id"], "gross_value": gross, "lines": lines, "total_withheld": withheld,
            "net_payable": round(gross - withheld, 2), "disclaimer": "illustrative table, not tax advice"}
