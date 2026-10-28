from datetime import date

import pytest

from gateway import access, catalog, executor, intents
from gateway.domains import grants, invoices, synthetic


@pytest.fixture
def admin():
    access.seed_demo()
    return access.get_principal("admin")


@pytest.mark.parametrize("tax_id, valid", [
    ("11.222.333/0001-81", True), ("11.222.333/0001-82", False), ("11111111111111", False),
    ("529.982.247-25", True), ("529.982.247-24", False), ("000.000.000-00", False),
])
def test_tax_id_check_digits(tax_id, valid, admin):
    assert executor.execute(admin, "invoices.validate_tax_id", {"tax_id": tax_id}).result["valid"] is valid


def test_synthetic_tax_ids_are_valid_and_deterministic():
    rows = synthetic.agreements()
    assert rows == synthetic.agreements.__wrapped__()
    assert all(invoices.validate_cnpj(r["grantee_tax_id"].replace(".", "").replace("/", "").replace("-", ""))
               for r in rows[:50])


def test_withholding_adds_up(admin):
    out = executor.execute(admin, "invoices.compute_withholding", {"id": "NF-100003"}).result
    assert out["net_payable"] == pytest.approx(out["gross_value"] - out["total_withheld"], abs=0.01)


def test_risk_rules():
    row = {"end_date": "2025-01-01", "status": "in_execution", "federal_value": 100.0, "disbursed_value": 10.0,
           "counterpart_value": 1.0}
    codes = {f["code"] for f in grants.risk_flags(row, date(2026, 1, 1))}
    assert codes == {"past_end_date", "low_execution", "thin_counterpart"}


def test_summary_ratios_are_bounded(admin):
    states = executor.execute(admin, "grants.summary_by_state", {}).result["states"]
    assert states and all(0 <= s["disbursement_ratio"] <= 1 for s in states)


@pytest.mark.parametrize("request_text, expected", [
    ("validar o CNPJ do fornecedor", "invoices.validate_tax_id"),
    ("quais convênios têm risco de atraso?", "grants.flag_risks"),
    ("calcular imposto retido da nota NF-100003", "invoices.compute_withholding"),
    ("resumo total por estado dos convenios", "grants.summary_by_state"),
    ("buscar notas fiscais do fornecedor Atlas", "invoices.search"),
    ("validr cnpj", "invoices.validate_tax_id"),  # typo
])
def test_intent_baseline(request_text, expected):
    tools = [t for t in catalog.native_tools() if t.domain in {"invoices", "grants"}]
    assert intents.suggest(request_text, tools)[0].tool == expected


def test_meta_tools_respect_role():
    access.seed_demo()
    auditor = access.get_principal("auditor")
    listed = executor.execute(auditor, "meta.list_tools").result
    assert set(listed["domains"]) == {"meta"}
