"""Deterministic synthetic data.

Same seed, same rows, on every machine — so tests and screenshots are
reproducible and no real company, person or agreement is ever involved.
Tax IDs are generated *with valid check digits* (they exercise the real
validation algorithm) but random bodies, so they belong to nobody on purpose.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from functools import lru_cache

STATES = ["MS", "MT", "GO", "SP", "PR", "BA", "PE", "PA", "AM", "RS"]
TOWNS = ["Vila Aurora", "Serra Clara", "Porto Lume", "Campo Novo do Sol", "Rio Ametista", "Lagoa Prata",
         "Alto Cedro", "Bela Brisa", "Monte Ônix", "Pedra Azul do Norte", "Nova Esperança do Vale", "Ipê Dourado"]
PROGRAMS = [
    ("P-1001", "Rural Water Access"), ("P-1002", "Family Farming Credit Support"),
    ("P-1003", "Seed Bank Modernization"), ("P-1004", "Cooperative Logistics Hubs"),
    ("P-1005", "Agroecology Technical Assistance"), ("P-1006", "Rural Roads Maintenance"),
]
STATUSES = ["in_execution", "in_execution", "in_execution", "awaiting_report", "report_under_review",
            "completed", "cancelled"]
SUPPLIER_WORDS = ["Atlas", "Boreal", "Cobalto", "Delta", "Equinócio", "Faro", "Granito", "Horizonte", "Íris"]
SUPPLIER_SUFFIX = ["Comércio Ltda", "Serviços S.A.", "Tecnologia ME", "Distribuidora Ltda", "Engenharia EIRELI"]
ITEMS = [
    ("software license", "service", 5.0), ("office chairs", "material", 0.0), ("network cabling", "hybrid", 2.0),
    ("cloud hosting", "service", 5.0), ("laptops", "material", 0.0), ("training course", "service", 2.0),
    ("solar panels installed", "hybrid", 3.0), ("printer toner", "material", 0.0),
]


def _cnpj_digits(base12: list[int]) -> list[int]:
    def dv(nums: list[int], weights: list[int]) -> int:
        r = sum(n * w for n, w in zip(nums, weights)) % 11
        return 0 if r < 2 else 11 - r
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = dv(base12, w1)
    d2 = dv(base12 + [d1], [6] + w1)
    return base12 + [d1, d2]


def fake_cnpj(rng: random.Random) -> str:
    base = [rng.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]
    d = _cnpj_digits(base)
    s = "".join(map(str, d))
    return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"


@lru_cache(maxsize=1)
def agreements() -> list[dict]:
    rng = random.Random(20261028)
    rows = []
    for i in range(240):
        program_id, program = rng.choice(PROGRAMS)
        start = date(2023, 1, 1) + timedelta(days=rng.randint(0, 900))
        value = round(rng.uniform(80_000, 4_500_000), 2)
        counterpart = round(value * rng.choice([0.01, 0.02, 0.05, 0.1]), 2)
        status = rng.choice(STATUSES)
        executed = {"completed": 1.0, "cancelled": rng.uniform(0, .3)}.get(status, rng.uniform(.1, .95))
        rows.append({
            "id": f"AG-{2023 + i % 3}-{1000 + i}",
            "program_id": program_id, "program": program,
            "town": rng.choice(TOWNS), "state": rng.choice(STATES),
            "grantee_tax_id": fake_cnpj(rng),
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=rng.choice([365, 540, 730]))).isoformat(),
            "federal_value": value, "counterpart_value": counterpart,
            "disbursed_value": round(value * executed, 2),
            "status": status,
        })
    return rows


@lru_cache(maxsize=1)
def invoices() -> list[dict]:
    rng = random.Random(42)
    suppliers = [(f"{w} {rng.choice(SUPPLIER_SUFFIX)}", fake_cnpj(rng)) for w in SUPPLIER_WORDS]
    rows = []
    for i in range(180):
        name, tax_id = rng.choice(suppliers)
        item, kind, iss = rng.choice(ITEMS)
        qty = rng.randint(1, 40)
        unit = round(rng.uniform(15, 4800), 2)
        rows.append({
            "id": f"NF-{100000 + i}", "series": rng.choice(["1", "2", "A1"]),
            "issued_on": (date(2026, 1, 1) + timedelta(days=rng.randint(0, 290))).isoformat(),
            "supplier": name, "supplier_tax_id": tax_id,
            "item": item, "kind": kind, "quantity": qty, "unit_price": unit,
            "gross_value": round(qty * unit, 2), "iss_rate_pct": iss,
            "town": rng.choice(TOWNS),
        })
    return rows
