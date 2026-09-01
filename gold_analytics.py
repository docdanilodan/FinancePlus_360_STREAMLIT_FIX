"""Calcoli deterministici e trasparenti di FINANCE_PLUS_GOLD_GENERALE."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import pandas as pd


def safe_div(numerator: Any, denominator: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        num = float(numerator)
        den = float(denominator)
    except (TypeError, ValueError):
        return default
    if den == 0:
        return default
    return num / den


def financial_kpis(row: Mapping[str, Any]) -> Dict[str, Optional[float]]:
    revenue = float(row.get("revenue") or 0)
    ebitda = float(row.get("ebitda") or 0)
    cash = float(row.get("cash") or 0)
    financial_debt = float(row.get("financial_debt") or 0)
    equity = float(row.get("equity") or 0)
    total_assets = float(row.get("total_assets") or 0)
    current_assets = float(row.get("current_assets") or 0)
    current_liabilities = float(row.get("current_liabilities") or 0)
    cfads = float(row.get("cash_flow_available") or 0)
    debt_service = float(row.get("debt_service") or 0)
    receivables = float(row.get("receivables") or 0)
    payables = float(row.get("payables") or 0)
    pfn = financial_debt - cash
    return {
        "revenue": revenue,
        "ebitda": ebitda,
        "ebitda_margin": safe_div(ebitda, revenue),
        "pfn": pfn,
        "pfn_ebitda": safe_div(pfn, ebitda),
        "dscr": safe_div(cfads, debt_service),
        "equity_ratio": safe_div(equity, total_assets),
        "current_ratio": safe_div(current_assets, current_liabilities),
        "receivables_days": safe_div(receivables * 365, revenue),
        "payables_days": safe_div(payables * 365, revenue),
        "leverage": safe_div(financial_debt, equity),
    }


def central_risk_kpis(row: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    row = row or {}
    granted = float(row.get("granted") or 0)
    utilized = float(row.get("utilized") or 0)
    overdue = float(row.get("overdue") or 0)
    past_due = float(row.get("past_due") or 0)
    return {
        "granted": granted,
        "utilized": utilized,
        "utilization": safe_div(utilized, granted),
        "available": granted - utilized,
        "overdue": overdue,
        "past_due": past_due,
        "anomaly_amount": overdue + past_due,
        "has_anomalies": (overdue + past_due) > 0 or bool(str(row.get("anomalies") or "").strip()),
    }


@dataclass(frozen=True)
class RatingResult:
    score: int
    rating: str
    pd_range: str
    judgement: str
    strengths: List[str]
    weaknesses: List[str]
    components: Dict[str, int]


def _band_score(
    value: Optional[float],
    bands: Sequence[tuple[float, int]],
    missing_score: int,
    higher_is_better: bool = True,
) -> int:
    if value is None or math.isnan(value):
        return missing_score
    ordered = sorted(bands, key=lambda item: item[0], reverse=not higher_is_better)
    if higher_is_better:
        for threshold, score in sorted(bands, reverse=True):
            if value >= threshold:
                return score
    else:
        for threshold, score in sorted(bands):
            if value <= threshold:
                return score
    return ordered[-1][1] if ordered else missing_score


def score_rating(kpis: Mapping[str, Optional[float]], cr: Optional[Mapping[str, Any]] = None) -> RatingResult:
    """Restituisce uno score gestionale 0-100, non un rating bancario ufficiale.

    I pesi massimi sono: DSCR 25, PFN/EBITDA 20, EBITDA margin 15,
    patrimonializzazione 15, current ratio 10, leverage 5 e CR 10.
    """

    dscr = kpis.get("dscr")
    pfn_ebitda = kpis.get("pfn_ebitda")
    margin = kpis.get("ebitda_margin")
    equity_ratio = kpis.get("equity_ratio")
    current_ratio = kpis.get("current_ratio")
    leverage = kpis.get("leverage")
    cr_kpis = central_risk_kpis(cr)

    components = {
        "DSCR": _band_score(dscr, [(1.50, 25), (1.25, 21), (1.10, 16), (1.00, 10), (0.80, 5)], 8),
        "PFN/EBITDA": _band_score(
            pfn_ebitda, [(0.0, 20), (1.5, 18), (2.5, 15), (3.5, 10), (5.0, 5)], 7, higher_is_better=False
        ),
        "EBITDA margin": _band_score(
            margin, [(0.20, 15), (0.12, 13), (0.08, 10), (0.04, 6), (0.0, 2)], 5
        ),
        "Equity ratio": _band_score(
            equity_ratio, [(0.35, 15), (0.25, 12), (0.15, 9), (0.08, 5), (0.0, 1)], 5
        ),
        "Current ratio": _band_score(
            current_ratio, [(1.50, 10), (1.20, 8), (1.00, 6), (0.80, 3), (0.0, 1)], 4
        ),
        "Leverage": _band_score(
            leverage, [(1.0, 5), (2.0, 4), (3.5, 3), (5.0, 1)], 2, higher_is_better=False
        ),
        "Centrale Rischi": 10,
    }
    utilization = cr_kpis.get("utilization")
    if cr_kpis["has_anomalies"]:
        components["Centrale Rischi"] = 1
    elif utilization is None:
        components["Centrale Rischi"] = 5
    elif utilization <= 0.70:
        components["Centrale Rischi"] = 10
    elif utilization <= 0.85:
        components["Centrale Rischi"] = 7
    elif utilization <= 1.00:
        components["Centrale Rischi"] = 4
    else:
        components["Centrale Rischi"] = 1

    score = max(0, min(100, int(round(sum(components.values())))))
    if score >= 90:
        rating, pd, judgement = "AAA", "< 0,5%", "Eccellente"
    elif score >= 82:
        rating, pd, judgement = "AA", "0,5% – 1,0%", "Molto buono"
    elif score >= 74:
        rating, pd, judgement = "A", "1,0% – 2,0%", "Buono"
    elif score >= 65:
        rating, pd, judgement = "BBB", "2,0% – 4,0%", "Adeguato"
    elif score >= 55:
        rating, pd, judgement = "BB", "4,0% – 8,0%", "Attenzione"
    elif score >= 45:
        rating, pd, judgement = "B", "8,0% – 15,0%", "Vulnerabile"
    elif score >= 30:
        rating, pd, judgement = "CCC", "15,0% – 30,0%", "Critico"
    else:
        rating, pd, judgement = "D", "> 30,0%", "Rischio molto elevato"

    strengths: List[str] = []
    weaknesses: List[str] = []
    if dscr is not None:
        (strengths if dscr >= 1.25 else weaknesses).append(f"DSCR pari a {dscr:.2f}x")
    else:
        weaknesses.append("DSCR non calcolabile: dati CFADS/debt service mancanti")
    if pfn_ebitda is not None:
        (strengths if pfn_ebitda <= 3.0 else weaknesses).append(f"PFN/EBITDA pari a {pfn_ebitda:.2f}x")
    if margin is not None:
        (strengths if margin >= 0.10 else weaknesses).append(f"EBITDA margin pari al {margin:.1%}")
    if equity_ratio is not None:
        (strengths if equity_ratio >= 0.20 else weaknesses).append(
            f"Patrimonializzazione pari al {equity_ratio:.1%}"
        )
    if cr_kpis["has_anomalies"]:
        weaknesses.append("Presenza di anomalie/scaduti nella Centrale Rischi")
    elif utilization is not None:
        (strengths if utilization <= 0.80 else weaknesses).append(
            f"Utilizzo affidamenti pari al {utilization:.1%}"
        )

    return RatingResult(score, rating, pd, judgement, strengths, weaknesses, components)


def annuity_payment(principal: float, annual_rate: float, years: int, payments_per_year: int = 12) -> float:
    periods = max(int(years * payments_per_year), 1)
    periodic_rate = annual_rate / payments_per_year
    if periodic_rate == 0:
        return principal / periods
    return principal * periodic_rate / (1 - (1 + periodic_rate) ** -periods)


def sustainable_loan(
    cfads: float,
    existing_annual_debt_service: float,
    target_dscr: float = 1.25,
    annual_rate: float = 0.06,
    years: int = 5,
) -> Dict[str, float]:
    if target_dscr <= 0:
        raise ValueError("Il DSCR obiettivo deve essere positivo.")
    annual_capacity = max(float(cfads) / target_dscr - float(existing_annual_debt_service), 0.0)
    monthly_capacity = annual_capacity / 12
    monthly_rate = annual_rate / 12
    periods = max(years * 12, 1)
    if monthly_rate == 0:
        principal = monthly_capacity * periods
    else:
        principal = monthly_capacity * (1 - (1 + monthly_rate) ** -periods) / monthly_rate
    return {
        "annual_capacity": annual_capacity,
        "monthly_capacity": monthly_capacity,
        "max_principal": max(principal, 0.0),
    }


def build_business_plan(
    start_year: int,
    base_revenue: float,
    years: int,
    revenue_growth: float,
    ebitda_margin: float,
    tax_rate: float,
    capex_ratio: float,
    working_capital_ratio: float,
    opening_pfn: float,
    annual_debt_service: float,
) -> pd.DataFrame:
    rows: List[Dict[str, float]] = []
    revenue = float(base_revenue)
    pfn = float(opening_pfn)
    previous_nwc = revenue * working_capital_ratio
    for offset in range(1, int(years) + 1):
        revenue *= 1 + revenue_growth
        ebitda = revenue * ebitda_margin
        taxes = max(ebitda * tax_rate, 0)
        capex = revenue * capex_ratio
        nwc = revenue * working_capital_ratio
        delta_nwc = nwc - previous_nwc
        cfads = ebitda - taxes - capex - delta_nwc
        dscr = safe_div(cfads, annual_debt_service)
        pfn = max(pfn + annual_debt_service - max(cfads, 0), 0)
        rows.append(
            {
                "Anno": start_year + offset,
                "Ricavi": revenue,
                "EBITDA": ebitda,
                "EBITDA %": ebitda_margin,
                "Imposte stimate": taxes,
                "CAPEX": capex,
                "Δ CCN": delta_nwc,
                "CFADS": cfads,
                "Servizio debito": annual_debt_service,
                "DSCR": dscr,
                "PFN finale": pfn,
            }
        )
        previous_nwc = nwc
    return pd.DataFrame(rows)


def normalize_statement(
    frame: pd.DataFrame,
    date_column: str,
    amount_column: Optional[str] = None,
    debit_column: Optional[str] = None,
    credit_column: Optional[str] = None,
    balance_column: Optional[str] = None,
) -> pd.DataFrame:
    if date_column not in frame.columns:
        raise ValueError("Colonna data non trovata.")
    out = pd.DataFrame()
    out["date"] = pd.to_datetime(frame[date_column], errors="coerce", dayfirst=True)
    if amount_column:
        out["amount"] = pd.to_numeric(frame[amount_column], errors="coerce").fillna(0)
    else:
        debit = pd.to_numeric(frame[debit_column], errors="coerce").fillna(0) if debit_column else 0
        credit = pd.to_numeric(frame[credit_column], errors="coerce").fillna(0) if credit_column else 0
        out["amount"] = credit - debit
    if balance_column:
        out["balance"] = pd.to_numeric(frame[balance_column], errors="coerce")
    out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    if out.empty:
        raise ValueError("Nessun movimento con data valida.")
    return out


def statement_kpis(frame: pd.DataFrame) -> Dict[str, Any]:
    inflows = float(frame.loc[frame["amount"] > 0, "amount"].sum())
    outflows = float(-frame.loc[frame["amount"] < 0, "amount"].sum())
    months = max(frame["date"].dt.to_period("M").nunique(), 1)
    result: Dict[str, Any] = {
        "from": frame["date"].min().date(),
        "to": frame["date"].max().date(),
        "transactions": int(len(frame)),
        "months": int(months),
        "inflows": inflows,
        "outflows": outflows,
        "net_flow": inflows - outflows,
        "monthly_inflows": inflows / months,
        "monthly_outflows": outflows / months,
        "coverage": safe_div(inflows, outflows),
        "negative_balance_days": None,
        "minimum_balance": None,
        "average_balance": None,
    }
    if "balance" in frame.columns and frame["balance"].notna().any():
        balances = frame["balance"].dropna()
        result["negative_balance_days"] = int((balances < 0).sum())
        result["minimum_balance"] = float(balances.min())
        result["average_balance"] = float(balances.mean())
    return result


def annual_comparison(financials: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for record in financials:
        kpi = financial_kpis(record)
        rows.append(
            {
                "Esercizio": int(record.get("fiscal_year") or 0),
                "Ricavi": kpi["revenue"],
                "EBITDA": kpi["ebitda"],
                "EBITDA %": kpi["ebitda_margin"],
                "PFN": kpi["pfn"],
                "PFN/EBITDA": kpi["pfn_ebitda"],
                "DSCR": kpi["dscr"],
                "Equity ratio": kpi["equity_ratio"],
                "Current ratio": kpi["current_ratio"],
            }
        )
    return pd.DataFrame(rows).sort_values("Esercizio") if rows else pd.DataFrame()
