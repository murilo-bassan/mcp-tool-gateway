"""Fills a fresh store with realistic activity so the panel has something to show.

    python scripts/demo_traffic.py

Runs entirely in-process against the synthetic domains — no network, no keys.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gateway import access, executor, registry, secrets_store  # noqa: E402

CALLS = [
    ("analyst", "invoices.validate_tax_id", {"tax_id": "11.222.333/0001-81"}),
    ("analyst", "invoices.validate_tax_id", {"tax_id": "529.982.247-24"}),
    ("analyst", "invoices.search", {"kind": "service", "limit": 5}),
    ("analyst", "invoices.compute_withholding", {"id": "NF-100003"}),
    ("analyst", "grants.flag_risks", {"state": "MS"}),
    ("analyst", "grants.summary_by_state", {}),
    ("analyst", "grants.search_agreements", {"state": "GO", "status": "awaiting_report"}),
    ("analyst", "grants.get_agreement", {"id": "AG-2024-1001"}),
    ("analyst", "invoices.get", {"id": "not-an-id"}),             # invalid_arguments
    ("auditor", "invoices.search", {}),                          # permission_denied
    ("admin", "meta.suggest_tool", {"request": "quais convênios estão atrasados?"}),
]


def main() -> None:
    access.seed_demo()
    rng = random.Random(7)
    for _ in range(60):
        who, tool, args = rng.choice(CALLS)
        executor.execute(access.get_principal(who), tool, args)

    analyst, admin = access.get_principal("analyst"), access.get_principal("admin")
    defn = registry.DynamicToolDefinition(
        name="weather.forecast", title="Daily forecast",
        description="Forecast for a city from an example upstream API.",
        input_schema={"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        http=registry.HttpBinding(url="https://api.example.org/v1/forecast/{city}",
                                  headers={"Authorization": "Bearer {{secret:weather_token}}"}),
        keywords=["previsao", "tempo", "forecast"],
    )
    if not registry.list_revisions():
        rev = registry.propose(defn, analyst)
        registry.review(rev.name, rev.revision, admin, approve=True)
        registry.propose(defn.model_copy(update={"title": "Daily forecast v2"}), analyst)
    secrets_store.put("analyst", "weather_token", "demo-token-not-real")
    print("demo traffic recorded")


if __name__ == "__main__":
    main()
