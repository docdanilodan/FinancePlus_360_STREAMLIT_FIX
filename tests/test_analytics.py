from __future__ import annotations

import pandas as pd
import pytest

from gold_analytics import (
    build_business_plan,
    financial_kpis,
    normalize_statement,
    score_rating,
    statement_kpis,
    sustainable_loan,
)


def test_financial_kpis_and_rating_are_consistent() -> None:
    row = {
        "revenue": 1_000_000,
        "ebitda": 150_000,
        "financial_debt": 300_000,
        "cash": 50_000,
        "cash_flow_available": 140_000,
        "debt_service": 100_000,
        "equity": 400_000,
        "total_assets": 1_200_000,
        "current_assets": 500_000,
        "current_liabilities": 350_000,
    }
    kpis = financial_kpis(row)
    assert kpis["ebitda_margin"] == pytest.approx(0.15)
    assert kpis["pfn"] == pytest.approx(250_000)
    assert kpis["pfn_ebitda"] == pytest.approx(1.6666667)
    assert kpis["dscr"] == pytest.approx(1.4)
    rating = score_rating(kpis, {"granted": 500_000, "utilized": 300_000})
    assert 0 <= rating.score <= 100
    assert rating.rating in {"AAA", "AA", "A", "BBB", "BB", "B", "CCC", "D"}


def test_anomaly_reduces_central_risk_component() -> None:
    kpis = financial_kpis(
        {
            "revenue": 1_000_000,
            "ebitda": 200_000,
            "financial_debt": 100_000,
            "cash": 20_000,
            "cash_flow_available": 160_000,
            "debt_service": 80_000,
            "equity": 500_000,
            "total_assets": 1_000_000,
            "current_assets": 400_000,
            "current_liabilities": 200_000,
        }
    )
    clean = score_rating(kpis, {"granted": 300_000, "utilized": 150_000})
    anomalous = score_rating(kpis, {"granted": 300_000, "utilized": 150_000, "past_due": 1_000})
    assert anomalous.components["Centrale Rischi"] < clean.components["Centrale Rischi"]
    assert anomalous.score < clean.score


def test_sustainable_loan_and_business_plan() -> None:
    capacity = sustainable_loan(250_000, 80_000, target_dscr=1.25, annual_rate=0.06, years=5)
    assert capacity["annual_capacity"] == pytest.approx(120_000)
    assert capacity["max_principal"] > 500_000
    plan = build_business_plan(2025, 1_000_000, 5, 0.05, 0.15, 0.28, 0.03, 0.12, 300_000, 100_000)
    assert len(plan) == 5
    assert list(plan["Anno"]) == [2026, 2027, 2028, 2029, 2030]
    assert plan.iloc[-1]["Ricavi"] > plan.iloc[0]["Ricavi"]


def test_statement_normalization() -> None:
    frame = pd.DataFrame(
        {
            "Data": ["01/01/2026", "02/01/2026", "03/02/2026"],
            "Importo": [1000, -250, 500],
            "Saldo": [1000, 750, 1250],
        }
    )
    normalized = normalize_statement(frame, "Data", amount_column="Importo", balance_column="Saldo")
    kpis = statement_kpis(normalized)
    assert kpis["inflows"] == pytest.approx(1500)
    assert kpis["outflows"] == pytest.approx(250)
    assert kpis["net_flow"] == pytest.approx(1250)
    assert kpis["months"] == 2
