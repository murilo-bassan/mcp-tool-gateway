"""Grants domain: public-transfer agreements (synthetic), search, aggregates and risk flags.

The risk rules are deterministic on purpose. An LLM is good at *explaining* a
flag to a person; it should not be the thing that decides one exists.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from gateway.catalog import CallContext, native, object_schema
from gateway.domains import synthetic
from gateway.errors import NotFound

_STATUS = {"enum": sorted(set(synthetic.STATUSES))}


@native("grants.search_agreements", title="Search agreements",
        description="Searches synthetic public-transfer agreements by state, town, program and status.",
        schema=object_schema({
            "state": {"type": "string", "minLength": 2, "maxLength": 2},
            "town": {"type": "string"}, "program_id": {"type": "string"}, "status": _STATUS,
            "min_value": {"type": "number", "minimum": 0},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
        }),
        keywords=("convenio", "convenios", "transferencia", "acordo", "repasse", "agreement"))
def search_agreements(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    rows = synthetic.agreements()
    if st := args.get("state"):
        rows = [r for r in rows if r["state"] == st.upper()]
    if town := args.get("town"):
        rows = [r for r in rows if town.lower() in r["town"].lower()]
    if pid := args.get("program_id"):
        rows = [r for r in rows if r["program_id"] == pid]
    if status := args.get("status"):
        rows = [r for r in rows if r["status"] == status]
    if (mv := args.get("min_value")) is not None:
        rows = [r for r in rows if r["federal_value"] >= mv]
    return {"total": len(rows), "items": rows[: args.get("limit", 20)]}


@native("grants.get_agreement", title="Get one agreement", description="Returns one agreement by id (e.g. AG-2024-1001).",
        schema=object_schema({"id": {"type": "string", "pattern": "^AG-\\d{4}-\\d+$"}}, ["id"]),
        keywords=("convenio", "detalhe", "agreement"))
def get_agreement(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    for row in synthetic.agreements():
        if row["id"] == args["id"]:
            return row
    raise NotFound(f"agreement {args['id']} not found")


@native("grants.summary_by_state", title="Totals by state",
        description="Agreement count, federal value and disbursement ratio per state, optionally for one program.",
        schema=object_schema({"program_id": {"type": "string"}}),
        keywords=("resumo", "total por estado", "panorama", "summary"))
def summary_by_state(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    acc: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0, "federal_value": 0.0, "disbursed": 0.0})
    for r in synthetic.agreements():
        if args.get("program_id") and r["program_id"] != args["program_id"]:
            continue
        a = acc[r["state"]]
        a["count"] += 1
        a["federal_value"] += r["federal_value"]
        a["disbursed"] += r["disbursed_value"]
    rows = [{"state": s, "count": int(v["count"]), "federal_value": round(v["federal_value"], 2),
             "disbursement_ratio": round(v["disbursed"] / v["federal_value"], 3) if v["federal_value"] else 0}
            for s, v in sorted(acc.items())]
    return {"states": rows}


def risk_flags(row: dict[str, Any], today: date) -> list[dict[str, str]]:
    flags = []
    end = date.fromisoformat(row["end_date"])
    ratio = row["disbursed_value"] / row["federal_value"]
    if row["status"] == "in_execution" and end < today:
        flags.append({"code": "past_end_date", "why": f"still in execution after {row['end_date']}"})
    if row["status"] == "in_execution" and end < today and ratio < 0.5:
        flags.append({"code": "low_execution", "why": f"only {ratio:.0%} disbursed past the end date"})
    if row["counterpart_value"] / row["federal_value"] < 0.015:
        flags.append({"code": "thin_counterpart", "why": "counterpart below 1.5% of the federal value"})
    if row["status"] == "awaiting_report" and (today - end).days > 60:
        flags.append({"code": "late_report", "why": f"report overdue by {(today - end).days} days"})
    return flags


@native("grants.flag_risks", title="Flag risky agreements",
        description="Applies deterministic risk rules (past end date, low execution, thin counterpart, late report).",
        schema=object_schema({
            "state": {"type": "string", "minLength": 2, "maxLength": 2},
            "as_of": {"type": "string", "format": "date"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
        }),
        keywords=("risco", "alerta", "atraso", "atrasado", "irregular", "auditoria", "risk", "overdue"))
def flag_risks(args: dict[str, Any], ctx: CallContext) -> dict[str, Any]:
    today = date.fromisoformat(args["as_of"]) if args.get("as_of") else date(2026, 10, 1)
    hits = []
    for r in synthetic.agreements():
        if args.get("state") and r["state"] != args["state"].upper():
            continue
        if flags := risk_flags(r, today):
            hits.append({"id": r["id"], "town": r["town"], "state": r["state"], "flags": flags})
    hits.sort(key=lambda h: -len(h["flags"]))
    return {"as_of": today.isoformat(), "flagged": len(hits), "items": hits[: args.get("limit", 25)]}
