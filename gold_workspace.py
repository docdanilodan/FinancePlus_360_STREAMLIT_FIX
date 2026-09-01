"""Interfaccia operativa unificata di FINANCE_PLUS_GOLD_GENERALE."""

from __future__ import annotations

import io
import os
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

import pandas as pd
import streamlit as st
from pypdf import PdfReader

import gold_data as db
from gold_analytics import (
    annuity_payment,
    annual_comparison,
    build_business_plan,
    central_risk_kpis,
    financial_kpis,
    normalize_statement,
    score_rating,
    statement_kpis,
    sustainable_loan,
)
from gold_reports import build_bank_dossier, safe_pdf_filename


APP_NAME = "FINANCE_PLUS_GOLD_GENERALE"
APP_VERSION = "V1.0"
PAGES = [
    "Dashboard", "Clienti", "Pratiche", "Documenti", "Analisi", "Mandati", "Banche",
    "Email", "Scadenzario", "Report", "Impostazioni",
]
DOCUMENT_CATEGORIES = [
    "Visura", "Bilancio", "Bozza bilancio", "Prospetto bilancio", "Analitico bilancio",
    "Centrale Rischi", "Estratto conto", "Documento identità", "Atto societario",
    "Contratto/Ordine", "Dichiarazione", "DURC", "Altro",
]


@dataclass(frozen=True)
class Hooks:
    mail_download_renderer: Optional[Callable[[Any], None]] = None
    accounts_renderer: Optional[Callable[[Any], None]] = None
    config_renderer: Optional[Callable[[Any], None]] = None
    connection_renderer: Optional[Callable[[Any], None]] = None
    save_load_renderer: Optional[Callable[[Any], None]] = None
    airtable_renderer: Optional[Callable[[], None]] = None


def _style() -> None:
    st.markdown(
        """
        <style>
        :root {--navy:#073f73;--blue:#155a93;--copper:#b87333;--line:#dbe5ed;--muted:#6a7c8d}
        [data-testid="stHeader"] {background:rgba(255,255,255,.92)}
        .block-container {max-width:1500px;padding-top:1rem;padding-bottom:3rem}
        .fp-head {background:linear-gradient(115deg,#052f59,#0b578f 70%,#1b6da3);color:#fff;
          border-bottom:4px solid var(--copper);padding:18px 22px;border-radius:12px;margin-bottom:14px}
        .fp-title {font-size:1.55rem;font-weight:850;letter-spacing:.035em}.fp-sub {opacity:.84;font-size:.82rem;margin-top:3px}
        .fp-section {font-size:1.26rem;font-weight:800;color:var(--navy);border-left:5px solid var(--copper);
          padding-left:10px;margin:8px 0 14px}
        .fp-card {background:#fff;border:1px solid var(--line);border-radius:11px;padding:13px 15px;min-height:92px;
          box-shadow:0 4px 14px rgba(7,63,115,.05)}
        .fp-card-label {font-size:.70rem;text-transform:uppercase;letter-spacing:.05em;color:#5a6e80;font-weight:750}
        .fp-card-value {font-size:1.48rem;color:#17364f;font-weight:850;margin-top:5px}.fp-card-note{font-size:.72rem;color:var(--muted)}
        .fp-alert {padding:11px 13px;background:#fff8ef;border:1px solid #eed6bb;border-left:4px solid var(--copper);
          border-radius:8px;color:#60472f;font-size:.84rem}
        div[data-testid="stHorizontalBlock"] div[role="radiogroup"] {gap:.25rem;flex-wrap:wrap}
        div[role="radiogroup"] label {border:1px solid #cfdae4;border-radius:8px;padding:.28rem .62rem;background:#fff}
        div[role="radiogroup"] label:has(input:checked) {background:var(--navy);border-color:var(--navy)}
        div[role="radiogroup"] label:has(input:checked) p {color:#fff!important;font-weight:700}
        .stButton>button[kind="primary"] {background:var(--navy);border-color:var(--navy)}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _header() -> None:
    st.markdown(
        f'<div class="fp-head"><div class="fp-title">{APP_NAME}</div>'
        f'<div class="fp-sub">Finance & Credit Intelligence · {APP_VERSION} · dati operativi reali</div></div>',
        unsafe_allow_html=True,
    )


def _section(title: str) -> None:
    st.markdown(f'<div class="fp-section">{title}</div>', unsafe_allow_html=True)


def _card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f'<div class="fp-card"><div class="fp-card-label">{label}</div>'
        f'<div class="fp-card-value">{value}</div><div class="fp-card-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def _money(value: Any, decimals: int = 0) -> str:
    try:
        text = f"€ {float(value or 0):,.{decimals}f}"
        return text.replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "€ 0"


def _percent(value: Any) -> str:
    try:
        return f"{float(value):.1%}"
    except (TypeError, ValueError):
        return "N/D"


def _ratio(value: Any) -> str:
    try:
        return f"{float(value):.2f}x"
    except (TypeError, ValueError):
        return "N/D"


def _client_options() -> List[Dict[str, Any]]:
    return db.list_clients()


def _client_select(label: str, key: str, allow_empty: bool = False) -> Optional[int]:
    clients = _client_options()
    if not clients:
        st.info("Crea prima almeno un cliente nella sezione Clienti.")
        return None
    ids: List[Optional[int]] = [None] if allow_empty else []
    ids.extend(int(item["id"]) for item in clients)
    labels = {int(item["id"]): item["name"] for item in clients}
    return st.selectbox(
        label,
        ids,
        format_func=lambda value: "Tutti i clienti" if value is None else labels[int(value)],
        key=key,
    )


def _show_dataframe(rows: Sequence[Mapping[str, Any]], columns: Mapping[str, str]) -> None:
    if not rows:
        st.info("Nessun dato disponibile.")
        return
    frame = pd.DataFrame(rows)
    available = [column for column in columns if column in frame.columns]
    st.dataframe(frame[available].rename(columns=columns), use_container_width=True, hide_index=True)


def render_dashboard() -> None:
    _section("Dashboard generale")
    metrics = db.dashboard_metrics()
    cols = st.columns(5)
    cards = [
        ("Clienti attivi", str(metrics["clients"]), "Anagrafiche operative"),
        ("Pratiche attive", str(metrics["active_practices"]), "Pipeline finanziaria"),
        ("Richieste in corso", _money(metrics["requested_amount"]), "Importo complessivo"),
        ("Documenti", str(metrics["documents"]), "Archivio classificato"),
        ("Scadenze urgenti", str(metrics["due_deadlines"]), "Scadute o previste oggi"),
    ]
    for column, card in zip(cols, cards):
        with column:
            _card(*card)

    if metrics["clients"] == 0:
        st.markdown(
            '<div class="fp-alert"><b>Prima configurazione:</b> crea un cliente, carica i documenti e inserisci '
            'almeno un esercizio di bilancio. La dashboard si aggiorna automaticamente.</div>',
            unsafe_allow_html=True,
        )
        return

    left, right = st.columns([1.45, 1])
    with left:
        st.subheader("Pratiche recenti")
        _show_dataframe(
            db.list_practices()[:10],
            {
                "client_name": "Cliente", "practice_type": "Tipo", "institution": "Istituto",
                "amount_requested": "Importo", "status": "Stato", "due_on": "Scadenza",
                "next_action": "Prossima azione",
            },
        )
    with right:
        st.subheader("Scadenze aperte")
        _show_dataframe(
            db.list_deadlines("Aperte")[:10],
            {"due_on": "Data", "client_name": "Cliente", "title": "Attività", "priority": "Priorità", "status": "Stato"},
        )

    ratings: List[Dict[str, Any]] = []
    for client in db.list_clients():
        financials = db.list_financials(client["id"])
        if not financials:
            continue
        risks = db.list_credit_risk(client["id"])
        result = score_rating(financial_kpis(financials[-1]), risks[-1] if risks else None)
        ratings.append({"Cliente": client["name"], "Score": result.score, "Rating": result.rating, "Giudizio": result.judgement})
    if ratings:
        st.subheader("Portafoglio rating gestionale")
        st.dataframe(ratings, use_container_width=True, hide_index=True)


def _client_form(defaults: Optional[Mapping[str, Any]] = None, key_prefix: str = "client") -> Dict[str, Any]:
    data = defaults or {}
    c1, c2, c3 = st.columns(3)
    name = c1.text_input("Denominazione *", value=str(data.get("name") or ""), key=f"{key_prefix}_name")
    vat = c2.text_input("Partita IVA (facoltativa)", value=str(data.get("vat") or ""), key=f"{key_prefix}_vat")
    tax_code = c3.text_input("Codice fiscale (facoltativo)", value=str(data.get("tax_code") or ""), key=f"{key_prefix}_tax")
    c1, c2, c3 = st.columns(3)
    legal_form = c1.text_input("Forma giuridica", value=str(data.get("legal_form") or ""), key=f"{key_prefix}_form")
    rea = c2.text_input("REA", value=str(data.get("rea") or ""), key=f"{key_prefix}_rea")
    ateco = c3.text_input("Codice ATECO", value=str(data.get("ateco") or ""), key=f"{key_prefix}_ateco")
    c1, c2, c3 = st.columns(3)
    pec = c1.text_input("PEC", value=str(data.get("pec") or ""), key=f"{key_prefix}_pec")
    email = c2.text_input("Email", value=str(data.get("email") or ""), key=f"{key_prefix}_email")
    phone = c3.text_input("Telefono", value=str(data.get("phone") or ""), key=f"{key_prefix}_phone")
    legal_address = st.text_input("Sede legale", value=str(data.get("legal_address") or ""), key=f"{key_prefix}_address")
    c1, c2, c3 = st.columns(3)
    administrator = c1.text_input("Amministratore", value=str(data.get("administrator") or ""), key=f"{key_prefix}_admin")
    manager = c2.text_input("Responsabile pratica", value=str(data.get("manager") or ""), key=f"{key_prefix}_manager")
    statuses = ["Attivo", "Prospect", "Sospeso", "Archiviato"]
    current_status = str(data.get("status") or "Attivo")
    status = c3.selectbox(
        "Stato", statuses, index=statuses.index(current_status) if current_status in statuses else 0,
        key=f"{key_prefix}_status",
    )
    notes = st.text_area("Note", value=str(data.get("notes") or ""), key=f"{key_prefix}_notes")
    return {
        "name": name, "vat": vat, "tax_code": tax_code, "legal_form": legal_form, "rea": rea,
        "ateco": ateco, "pec": pec, "email": email, "phone": phone, "legal_address": legal_address,
        "administrator": administrator, "manager": manager, "status": status, "notes": notes,
    }


def render_clients() -> None:
    _section("Clienti 360")
    tab_list, tab_new, tab_edit = st.tabs(["Elenco e fascicolo", "Nuovo cliente", "Modifica anagrafica"])
    with tab_list:
        query = st.text_input("Cerca cliente", placeholder="Denominazione, P.IVA, C.F., PEC o email", key="client_search")
        clients = db.list_clients(query)
        _show_dataframe(
            clients,
            {
                "name": "Denominazione", "vat": "P.IVA", "tax_code": "C.F.", "manager": "Responsabile",
                "status": "Stato", "practice_count": "Pratiche", "document_count": "Documenti",
            },
        )
        if clients:
            labels = {row["id"]: row["name"] for row in clients}
            selected_id = st.selectbox("Apri fascicolo", list(labels), format_func=lambda value: labels[value], key="client_open")
            selected = db.get_client(selected_id)
            if selected:
                st.subheader(selected["name"])
                a, b, c, d = st.columns(4)
                a.metric("P.IVA", selected.get("vat") or "Non indicata")
                b.metric("Codice fiscale", selected.get("tax_code") or "Non indicato")
                c.metric("Pratiche", len(db.list_practices(selected_id)))
                d.metric("Documenti", len(db.list_documents(selected_id)))
                info = pd.DataFrame(
                    [
                        ["Forma giuridica", selected.get("legal_form") or "—"],
                        ["REA / ATECO", f"{selected.get('rea') or '—'} / {selected.get('ateco') or '—'}"],
                        ["Sede", selected.get("legal_address") or "—"],
                        ["Amministratore", selected.get("administrator") or "—"],
                        ["PEC / Email", f"{selected.get('pec') or '—'} / {selected.get('email') or '—'}"],
                        ["Responsabile", selected.get("manager") or "—"],
                    ],
                    columns=["Dato", "Valore"],
                )
                st.dataframe(info, use_container_width=True, hide_index=True)
                missing = db.missing_document_categories(selected_id)
                if missing:
                    st.warning("Documenti essenziali mancanti: " + ", ".join(missing))
                else:
                    st.success("Fascicolo essenziale completo.")

    with tab_new:
        with st.form("new_client_form", clear_on_submit=True):
            payload = _client_form(key_prefix="new_client")
            submitted = st.form_submit_button("Salva cliente", type="primary")
        if submitted:
            try:
                client_id = db.save_client(payload)
                st.success(f"Cliente creato correttamente (ID {client_id}).")
            except Exception as exc:
                st.error(str(exc))

    with tab_edit:
        clients = db.list_clients()
        if not clients:
            st.info("Non ci sono clienti da modificare.")
        else:
            labels = {row["id"]: row["name"] for row in clients}
            selected_id = st.selectbox("Cliente da modificare", list(labels), format_func=lambda value: labels[value], key="edit_client_id")
            current = db.get_client(selected_id) or {}
            with st.form(f"edit_client_form_{selected_id}"):
                payload = _client_form(current, key_prefix=f"edit_client_{selected_id}")
                submitted = st.form_submit_button("Aggiorna anagrafica", type="primary")
            if submitted:
                try:
                    db.save_client(payload, selected_id)
                    st.success("Anagrafica aggiornata.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


def render_practices() -> None:
    _section("Pratiche finanziarie")
    tab_pipeline, tab_new = st.tabs(["Pipeline", "Nuova pratica"])
    with tab_pipeline:
        client_id = _client_select("Filtra per cliente", "practice_filter_client", allow_empty=True)
        rows = db.list_practices(client_id)
        _show_dataframe(
            rows,
            {
                "client_name": "Cliente", "practice_type": "Tipo", "institution": "Istituto",
                "amount_requested": "Importo richiesto", "status": "Stato", "priority": "Priorità",
                "completeness": "Completezza %", "probability": "Probabilità %", "due_on": "Scadenza",
                "next_action": "Prossima azione",
            },
        )
    with tab_new:
        client_id = _client_select("Cliente *", "new_practice_client")
        if client_id:
            with st.form("new_practice_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                practice_type = c1.selectbox(
                    "Tipo pratica *", ["Chirografario", "Mutuo", "Leasing", "Factoring", "Anticipo fatture", "Fido", "Altro"]
                )
                institution = c2.text_input("Istituto / intermediario")
                amount_requested = c3.number_input("Importo richiesto", min_value=0.0, step=10000.0)
                c1, c2, c3 = st.columns(3)
                status = c1.selectbox("Stato", ["Da avviare", "Raccolta documenti", "Istruttoria", "Integrazione", "Delibera", "Erogazione", "Erogata", "Respinta", "Chiusa"])
                priority = c2.selectbox("Priorità", ["Alta", "Media", "Bassa"], index=1)
                opened_on = c3.date_input("Data apertura", value=date.today())
                c1, c2, c3 = st.columns(3)
                due_on = c1.date_input("Scadenza indicativa", value=date.today())
                completeness = c2.slider("Completezza dossier %", 0, 100, 0)
                probability = c3.slider("Probabilità indicativa %", 0, 100, 0)
                next_action = st.text_input("Prossima azione")
                notes = st.text_area("Note")
                submitted = st.form_submit_button("Salva pratica", type="primary")
            if submitted:
                try:
                    db.save_practice(
                        {
                            "client_id": client_id, "practice_type": practice_type, "institution": institution,
                            "amount_requested": amount_requested, "status": status, "priority": priority,
                            "opened_on": opened_on, "due_on": due_on, "completeness": completeness,
                            "probability": probability, "next_action": next_action, "notes": notes,
                        }
                    )
                    st.success("Pratica registrata.")
                except Exception as exc:
                    st.error(str(exc))


def _practice_select(client_id: int, label: str, key: str) -> Optional[int]:
    rows = db.list_practices(client_id)
    if not rows:
        st.caption("Nessuna pratica collegabile per il cliente selezionato.")
        return None
    labels = {
        row["id"]: f"#{row['id']} - {row['practice_type']} - {_money(row['amount_requested'])} - {row['status']}"
        for row in rows
    }
    options: List[Optional[int]] = [None] + list(labels)
    return st.selectbox(
        label, options, format_func=lambda value: "Nessuna pratica" if value is None else labels[value], key=key
    )


def render_mandates() -> None:
    _section("Mandati e compensi")
    tab_list, tab_new = st.tabs(["Riepilogo compensi", "Nuovo mandato"])
    with tab_list:
        client_id = _client_select("Filtra per cliente", "mandate_filter", allow_empty=True)
        rows = db.list_mandates(client_id)
        enriched = []
        for row in rows:
            enriched.append(
                {
                    **row,
                    "residual_fee": max(float(row.get("calculated_fee") or 0) - float(row.get("deposits") or 0), 0),
                }
            )
        _show_dataframe(
            enriched,
            {
                "client_name": "Cliente", "subject": "Oggetto", "practice_type": "Pratica",
                "fee_basis": "Base compenso", "base_amount": "Importo base", "percentage": "%",
                "minimum_fee": "Minimo", "calculated_fee": "Compenso", "deposits": "Acconti",
                "residual_fee": "Residuo", "due_on": "Scadenza", "status": "Stato",
            },
        )
        if enriched:
            total = sum(float(row["calculated_fee"] or 0) for row in enriched)
            collected = sum(float(row["deposits"] or 0) for row in enriched)
            c1, c2, c3 = st.columns(3)
            c1.metric("Compensi maturati", _money(total))
            c2.metric("Acconti/incassi", _money(collected))
            c3.metric("Residuo", _money(max(total - collected, 0)))
    with tab_new:
        client_id = _client_select("Cliente *", "mandate_client")
        if client_id:
            practice_id = _practice_select(client_id, "Pratica collegata", "mandate_practice")
            with st.form("new_mandate", clear_on_submit=True):
                subject = st.text_input("Oggetto del mandato *")
                c1, c2, c3 = st.columns(3)
                signed_on = c1.date_input("Data mandato", value=date.today())
                fee_basis = c2.selectbox("Base del compenso", ["Importo richiesto", "Importo deliberato", "Importo erogato", "Importo fisso"])
                status = c3.selectbox("Stato", ["Bozza", "Attivo", "Sospeso", "Concluso"])
                c1, c2, c3, c4 = st.columns(4)
                base_amount = c1.number_input("Importo base", min_value=0.0, step=10000.0)
                percentage = c2.number_input("Percentuale %", min_value=0.0, max_value=100.0, step=0.1)
                minimum_fee = c3.number_input("Compenso minimo", min_value=0.0, step=500.0)
                deposits = c4.number_input("Acconti già incassati", min_value=0.0, step=500.0)
                due_on = st.date_input("Scadenza compenso", value=date.today())
                notes = st.text_area("Note")
                preview_fee = max(base_amount * percentage / 100, minimum_fee)
                st.info(f"Compenso calcolato: {_money(preview_fee)} - residuo dopo acconti: {_money(max(preview_fee-deposits, 0))}")
                submitted = st.form_submit_button("Registra mandato", type="primary")
            if submitted:
                try:
                    db.save_mandate(
                        {
                            "client_id": client_id, "practice_id": practice_id, "subject": subject,
                            "signed_on": signed_on, "fee_basis": fee_basis, "base_amount": base_amount,
                            "percentage": percentage, "minimum_fee": minimum_fee, "deposits": deposits,
                            "due_on": due_on, "status": status, "notes": notes,
                        }
                    )
                    st.success("Mandato registrato.")
                except Exception as exc:
                    st.error(str(exc))


def render_banks() -> None:
    _section("Banche, factoring e confronto offerte")
    tab_compare, tab_new = st.tabs(["Confronto condizioni", "Nuova offerta"])
    with tab_compare:
        client_id = _client_select("Filtra per cliente", "offer_filter", allow_empty=True)
        rows = db.list_bank_offers(client_id)
        compared = []
        for row in rows:
            monthly = annuity_payment(
                float(row.get("amount") or 0), float(row.get("tan") or 0) / 100,
                max(int(row.get("duration_months") or 0), 1) / 12, payments_per_year=12,
            ) if int(row.get("duration_months") or 0) else 0
            compared.append({**row, "estimated_payment": monthly})
        _show_dataframe(
            compared,
            {
                "client_name": "Cliente", "institution": "Istituto", "product": "Prodotto",
                "amount": "Importo", "tan": "TAN %", "taeg": "TAEG %", "duration_months": "Mesi",
                "prepayment_months": "Preamm.", "fees": "Costi", "estimated_payment": "Rata stimata",
                "guarantees": "Garanzie", "status": "Stato", "offer_date": "Data",
            },
        )
        if compared:
            valid = [row for row in compared if float(row.get("taeg") or 0) > 0]
            if valid:
                best = min(valid, key=lambda row: float(row["taeg"]))
                st.success(f"TAEG più basso registrato: {best['institution']} - {best['product']} ({best['taeg']:.2f}%).")
        st.caption("La rata è una stima a rata costante e non include costi accessori non caricati.")
    with tab_new:
        client_id = _client_select("Cliente *", "offer_client")
        if client_id:
            practice_id = _practice_select(client_id, "Pratica collegata", "offer_practice")
            with st.form("new_bank_offer", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                institution = c1.text_input("Istituto / intermediario *")
                product = c2.selectbox("Prodotto *", ["Chirografario", "Mutuo", "Factoring", "Anticipo fatture", "Leasing", "Fido", "Altro"])
                amount = c3.number_input("Importo offerto", min_value=0.0, step=10000.0)
                c1, c2, c3, c4 = st.columns(4)
                tan = c1.number_input("TAN %", min_value=0.0, max_value=50.0, step=0.05)
                taeg = c2.number_input("TAEG %", min_value=0.0, max_value=50.0, step=0.05)
                duration = c3.number_input("Durata mesi", min_value=0, max_value=360, step=1)
                prepayment = c4.number_input("Preammortamento mesi", min_value=0, max_value=60, step=1)
                c1, c2, c3 = st.columns(3)
                fees = c1.number_input("Costi iniziali", min_value=0.0, step=100.0)
                offer_date = c2.date_input("Data offerta", value=date.today())
                status = c3.selectbox("Stato", ["Da valutare", "In negoziazione", "Accettata", "Rifiutata", "Scaduta"])
                guarantees = st.text_input("Garanzie / covenant")
                notes = st.text_area("Note")
                submitted = st.form_submit_button("Salva offerta", type="primary")
            if submitted:
                try:
                    db.save_bank_offer(
                        {
                            "client_id": client_id, "practice_id": practice_id, "institution": institution,
                            "product": product, "amount": amount, "tan": tan, "taeg": taeg,
                            "duration_months": duration, "prepayment_months": prepayment, "fees": fees,
                            "offer_date": offer_date, "status": status, "guarantees": guarantees, "notes": notes,
                        }
                    )
                    st.success("Offerta registrata.")
                except Exception as exc:
                    st.error(str(exc))


def _preview_document(name: str, content: bytes) -> None:
    suffix = Path(name).suffix.lower()
    try:
        if suffix == ".pdf":
            reader = PdfReader(io.BytesIO(content))
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages[:5])
            st.text_area("Anteprima testo (prime 5 pagine)", text[:25000] or "PDF senza testo estraibile.", height=300)
        elif suffix in {".txt", ".csv", ".xml", ".json", ".eml"}:
            st.text_area("Anteprima", content.decode("utf-8", errors="replace")[:25000], height=300)
        elif suffix in {".xlsx", ".xls"}:
            st.dataframe(pd.read_excel(io.BytesIO(content)).head(100), use_container_width=True)
        elif suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            st.image(content, caption=name, use_container_width=True)
        else:
            st.info("Anteprima non disponibile per questo formato; il download resta disponibile.")
    except Exception as exc:
        st.warning(f"Impossibile generare l'anteprima: {exc}")


def render_documents() -> None:
    _section("Archivio documentale")
    tab_archive, tab_upload = st.tabs(["Consulta archivio", "Carica documenti"])
    with tab_archive:
        c1, c2, c3 = st.columns([2, 1, 1])
        query = c1.text_input("Cerca", placeholder="Nome file o cliente", key="document_search")
        category = c2.selectbox("Categoria", ["Tutti"] + DOCUMENT_CATEGORIES, key="document_category_filter")
        client_id = _client_select("Cliente", "document_client_filter", allow_empty=True)
        rows = db.list_documents(client_id=client_id, category=category, query=query)
        _show_dataframe(
            rows,
            {
                "client_name": "Cliente", "original_name": "Documento", "category": "Categoria",
                "document_date": "Data", "fiscal_year": "Esercizio", "source": "Origine",
                "verification_status": "Verifica", "size_bytes": "Byte",
            },
        )
        if rows:
            labels = {row["id"]: f"{row['client_name']} — {row['original_name']}" for row in rows}
            selected_id = st.selectbox("Apri documento", list(labels), format_func=lambda value: labels[value], key="document_open")
            record, content = db.read_document(selected_id)
            mime = "application/pdf" if record["original_name"].lower().endswith(".pdf") else "application/octet-stream"
            st.download_button("Scarica documento", content, file_name=record["original_name"], mime=mime, type="primary")
            _preview_document(record["original_name"], content)

    with tab_upload:
        client_id = _client_select("Cliente *", "upload_client")
        if client_id:
            category = st.selectbox("Categoria *", DOCUMENT_CATEGORIES, key="upload_category")
            c1, c2, c3 = st.columns(3)
            document_date = c1.date_input("Data documento", value=date.today(), key="upload_date")
            fiscal_year = c2.number_input("Esercizio", min_value=1990, max_value=2100, value=date.today().year, step=1)
            verification = c3.selectbox("Stato verifica", ["Da verificare", "Verificato", "Incompleto", "Scaduto"])
            source = st.selectbox("Origine", ["Caricamento manuale", "Email Gmail", "Email Aruba", "Airtable", "Altro"])
            notes = st.text_area("Note documento", key="upload_notes")
            files = st.file_uploader(
                "Seleziona uno o più file",
                accept_multiple_files=True,
                type=["pdf", "doc", "docx", "xls", "xlsx", "csv", "txt", "xml", "json", "eml", "png", "jpg", "jpeg", "webp", "zip"],
            )
            if st.button("Archivia documenti", type="primary", disabled=not files):
                saved = duplicates = 0
                for uploaded in files or []:
                    try:
                        _, created = db.save_document(
                            client_id, uploaded.name, uploaded.getvalue(), category, document_date,
                            int(fiscal_year), source, verification, notes,
                        )
                        saved += int(created)
                        duplicates += int(not created)
                    except Exception as exc:
                        st.error(f"{uploaded.name}: {exc}")
                if saved:
                    st.success(f"Archiviati {saved} documenti.")
                if duplicates:
                    st.info(f"Ignorati {duplicates} duplicati già presenti per il cliente.")


def _financial_input(client_id: int) -> None:
    with st.form("financial_form", clear_on_submit=False):
        year = st.number_input("Esercizio *", min_value=1990, max_value=2100, value=date.today().year - 1, step=1)
        st.caption("Inserire importi in euro. I campi non disponibili possono rimanere a zero.")
        c1, c2, c3, c4 = st.columns(4)
        revenue = c1.number_input("Ricavi", step=10000.0)
        ebitda = c2.number_input("EBITDA", step=10000.0)
        ebit = c3.number_input("EBIT", step=10000.0)
        net_income = c4.number_input("Utile netto", step=10000.0)
        c1, c2, c3, c4 = st.columns(4)
        cfads = c1.number_input("CFADS / cash flow disponibile", step=10000.0)
        debt_service = c2.number_input("Servizio annuo del debito", step=10000.0)
        cash = c3.number_input("Disponibilità liquide", step=10000.0)
        financial_debt = c4.number_input("Debiti finanziari", step=10000.0)
        c1, c2, c3, c4 = st.columns(4)
        equity = c1.number_input("Patrimonio netto", step=10000.0)
        total_assets = c2.number_input("Totale attivo", step=10000.0)
        total_debt = c3.number_input("Debiti totali", step=10000.0)
        current_assets = c4.number_input("Attivo corrente", step=10000.0)
        c1, c2, c3 = st.columns(3)
        current_liabilities = c1.number_input("Passivo corrente", step=10000.0)
        receivables = c2.number_input("Crediti commerciali", step=10000.0)
        payables = c3.number_input("Debiti fornitori", step=10000.0)
        notes = st.text_area("Note")
        submitted = st.form_submit_button("Salva/aggiorna esercizio", type="primary")
    if submitted:
        try:
            db.save_financial(
                {
                    "client_id": client_id, "fiscal_year": year, "revenue": revenue, "ebitda": ebitda,
                    "ebit": ebit, "net_income": net_income, "cash_flow_available": cfads,
                    "debt_service": debt_service, "cash": cash, "financial_debt": financial_debt,
                    "equity": equity, "total_assets": total_assets, "total_debt": total_debt,
                    "current_assets": current_assets, "current_liabilities": current_liabilities,
                    "receivables": receivables, "payables": payables, "notes": notes,
                }
            )
            st.success("Dati di bilancio salvati.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def _render_financial_analysis(client_id: int) -> None:
    _financial_input(client_id)
    rows = db.list_financials(client_id)
    if not rows:
        st.info("Inserisci almeno un esercizio per calcolare KPI e trend.")
        return
    comparison = annual_comparison(rows)
    shown = comparison.copy()
    for column in ["EBITDA %", "Equity ratio"]:
        shown[column] = shown[column].map(_percent)
    for column in ["PFN/EBITDA", "DSCR", "Current ratio"]:
        shown[column] = shown[column].map(_ratio)
    for column in ["Ricavi", "EBITDA", "PFN"]:
        shown[column] = shown[column].map(_money)
    st.dataframe(shown, use_container_width=True, hide_index=True)
    chart = comparison.set_index("Esercizio")[["Ricavi", "EBITDA", "PFN"]]
    st.line_chart(chart)


def _render_credit_risk(client_id: int) -> None:
    with st.form("credit_risk_form"):
        c1, c2, c3 = st.columns(3)
        reference_date = c1.date_input("Data riferimento", value=date.today())
        granted = c2.number_input("Accordato complessivo", min_value=0.0, step=10000.0)
        utilized = c3.number_input("Utilizzato complessivo", min_value=0.0, step=10000.0)
        c1, c2, c3, c4 = st.columns(4)
        overdue = c1.number_input("Scaduto", min_value=0.0, step=1000.0)
        past_due = c2.number_input("Past due / sofferenze", min_value=0.0, step=1000.0)
        guarantees = c3.number_input("Garanzie", min_value=0.0, step=10000.0)
        number_banks = c4.number_input("Numero intermediari", min_value=0, step=1)
        anomalies = st.text_area("Anomalie e note")
        submitted = st.form_submit_button("Salva rilevazione CR", type="primary")
    if submitted:
        try:
            db.save_credit_risk(
                {
                    "client_id": client_id, "reference_date": reference_date, "granted": granted,
                    "utilized": utilized, "overdue": overdue, "past_due": past_due,
                    "guarantees": guarantees, "number_banks": number_banks, "anomalies": anomalies,
                }
            )
            st.success("Rilevazione Centrale Rischi salvata.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    rows = db.list_credit_risk(client_id)
    if rows:
        frame_rows = []
        for row in rows:
            item = central_risk_kpis(row)
            frame_rows.append(
                {
                    "Data": row["reference_date"], "Accordato": _money(item["granted"]),
                    "Utilizzato": _money(item["utilized"]), "Utilizzo": _percent(item["utilization"]),
                    "Disponibile": _money(item["available"]), "Scaduto": _money(item["overdue"]),
                    "Past due": _money(item["past_due"]), "Intermediari": row["number_banks"],
                }
            )
        st.dataframe(frame_rows, use_container_width=True, hide_index=True)


def _read_spreadsheet(uploaded: Any) -> pd.DataFrame:
    suffix = Path(uploaded.name).suffix.lower()
    content = uploaded.getvalue()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(io.BytesIO(content))
    try:
        return pd.read_csv(io.BytesIO(content), sep=None, engine="python")
    except UnicodeDecodeError:
        return pd.read_csv(io.BytesIO(content), sep=None, engine="python", encoding="latin-1")


def _render_bank_account() -> None:
    st.caption("Il file deve contenere una colonna data e un importo con segno, oppure colonne dare/avere separate.")
    uploaded = st.file_uploader("Estratto conto CSV/XLSX", type=["csv", "xlsx", "xls"], key="statement_file")
    if not uploaded:
        return
    try:
        frame = _read_spreadsheet(uploaded)
    except Exception as exc:
        st.error(f"File non leggibile: {exc}")
        return
    st.dataframe(frame.head(30), use_container_width=True)
    columns = list(frame.columns)
    date_column = st.selectbox("Colonna data", columns)
    mode = st.radio("Struttura importi", ["Importo con segno", "Dare/Avere separati"], horizontal=True)
    amount = debit = credit = None
    if mode == "Importo con segno":
        amount = st.selectbox("Colonna importo (+ entrata / - uscita)", columns)
    else:
        debit = st.selectbox("Colonna uscite / dare", columns, key="statement_debit")
        credit = st.selectbox("Colonna entrate / avere", columns, key="statement_credit")
    balance_options: List[Optional[str]] = [None] + columns
    balance = st.selectbox("Colonna saldo (facoltativa)", balance_options, format_func=lambda x: "Non presente" if x is None else str(x))
    if st.button("Calcola KPI conto corrente", type="primary"):
        try:
            normalized = normalize_statement(frame, date_column, amount, debit, credit, balance)
            kpis = statement_kpis(normalized)
            cols = st.columns(4)
            for column, card in zip(
                cols,
                [
                    ("Entrate", _money(kpis["inflows"]), f"{kpis['months']} mesi"),
                    ("Uscite", _money(kpis["outflows"]), "Movimenti in addebito"),
                    ("Flusso netto", _money(kpis["net_flow"]), "Entrate meno uscite"),
                    ("Copertura flussi", _ratio(kpis["coverage"]), "Entrate / uscite"),
                ],
            ):
                with column:
                    _card(*card)
            if kpis["minimum_balance"] is not None:
                st.info(
                    f"Saldo medio {_money(kpis['average_balance'])}; saldo minimo {_money(kpis['minimum_balance'])}; "
                    f"rilevazioni negative {kpis['negative_balance_days']}."
                )
            monthly = normalized.assign(month=normalized["date"].dt.to_period("M").astype(str)).groupby("month")["amount"].sum()
            st.bar_chart(monthly)
        except Exception as exc:
            st.error(str(exc))


def _current_rating(client_id: int):
    financials = db.list_financials(client_id)
    if not financials:
        return None, None, None
    risks = db.list_credit_risk(client_id)
    latest_financial = financials[-1]
    latest_risk = risks[-1] if risks else None
    kpis = financial_kpis(latest_financial)
    return score_rating(kpis, latest_risk), kpis, latest_financial


def _render_rating(client_id: int) -> None:
    result, kpis, latest = _current_rating(client_id)
    if not result:
        st.info("Inserisci almeno un esercizio di bilancio per generare lo score.")
        return
    a, b, c, d = st.columns(4)
    a.metric("Score", f"{result.score}/100")
    b.metric("Rating gestionale", result.rating)
    c.metric("Giudizio", result.judgement)
    d.metric("PD indicativa", result.pd_range)
    st.caption("Pre-valutazione interna: non coincide con il modello ufficiale MCC o con rating proprietari bancari.")
    st.bar_chart(pd.Series(result.components, name="Punti"))
    left, right = st.columns(2)
    with left:
        st.success("Punti di forza\n\n" + ("\n\n".join(f"• {x}" for x in result.strengths) or "Nessuno rilevato"))
    with right:
        st.warning("Criticità\n\n" + ("\n\n".join(f"• {x}" for x in result.weaknesses) or "Nessuna rilevata"))

    st.subheader("Capacità indicativa nuovo debito")
    c1, c2, c3 = st.columns(3)
    target_dscr = c1.number_input("DSCR obiettivo", min_value=1.0, max_value=3.0, value=1.25, step=0.05)
    rate = c2.number_input("Tasso annuo %", min_value=0.0, max_value=30.0, value=6.0, step=0.25) / 100
    years = c3.number_input("Durata anni", min_value=1, max_value=20, value=5, step=1)
    capacity = sustainable_loan(
        float(latest.get("cash_flow_available") or 0), float(latest.get("debt_service") or 0), target_dscr, rate, int(years)
    )
    st.info(
        f"Servizio annuo aggiuntivo sostenibile: {_money(capacity['annual_capacity'])}. "
        f"Capitale teorico massimo: **{_money(capacity['max_principal'])}**. "
        "La stima richiede verifica bancaria e stress test."
    )


def _render_business_plan(client_id: int) -> None:
    financials = db.list_financials(client_id)
    last = financials[-1] if financials else {}
    st.caption("Proiezione deterministica a scenari. Le ipotesi restano modificabili e devono essere documentate.")
    c1, c2, c3 = st.columns(3)
    base_revenue = c1.number_input("Ricavi base", min_value=0.0, value=float(last.get("revenue") or 0), step=10000.0)
    start_year = c2.number_input("Anno base", min_value=1990, max_value=2100, value=int(last.get("fiscal_year") or date.today().year), step=1)
    years = c3.number_input("Anni previsionali", min_value=1, max_value=10, value=5, step=1)
    c1, c2, c3, c4 = st.columns(4)
    growth = c1.number_input("Crescita ricavi %", value=5.0, step=0.5) / 100
    margin = c2.number_input("EBITDA margin %", value=12.0, step=0.5) / 100
    tax = c3.number_input("Aliquota fiscale stimata %", value=28.0, step=0.5) / 100
    capex = c4.number_input("CAPEX / ricavi %", value=3.0, step=0.5) / 100
    c1, c2, c3 = st.columns(3)
    nwc = c1.number_input("CCN / ricavi %", value=15.0, step=0.5) / 100
    opening_pfn = c2.number_input("PFN iniziale", min_value=0.0, value=max(float(last.get("financial_debt") or 0) - float(last.get("cash") or 0), 0), step=10000.0)
    annual_debt_service = c3.number_input("Servizio annuo debito", min_value=0.0, value=float(last.get("debt_service") or 0), step=10000.0)
    plan = build_business_plan(
        int(start_year), base_revenue, int(years), growth, margin, tax, capex, nwc, opening_pfn, annual_debt_service
    )
    shown = plan.copy()
    shown["EBITDA %"] = shown["EBITDA %"].map(_percent)
    shown["DSCR"] = shown["DSCR"].map(_ratio)
    for column in ["Ricavi", "EBITDA", "Imposte stimate", "CAPEX", "Δ CCN", "CFADS", "Servizio debito", "PFN finale"]:
        shown[column] = shown[column].map(_money)
    st.dataframe(shown, use_container_width=True, hide_index=True)
    st.line_chart(plan.set_index("Anno")[["Ricavi", "EBITDA", "CFADS", "PFN finale"]])
    st.download_button(
        "Scarica piano CSV", plan.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"business_plan_cliente_{client_id}.csv", mime="text/csv",
    )


def render_analysis() -> None:
    _section("Analisi finanziaria e creditizia")
    client_id = _client_select("Cliente da analizzare", "analysis_client")
    if not client_id:
        return
    client = db.get_client(client_id)
    st.subheader(client["name"] if client else "Cliente")
    tabs = st.tabs(["Bilanci e KPI", "Centrale Rischi", "Conti Correnti", "Rating / MCC", "Business Plan"])
    with tabs[0]:
        _render_financial_analysis(client_id)
    with tabs[1]:
        _render_credit_risk(client_id)
    with tabs[2]:
        _render_bank_account()
    with tabs[3]:
        _render_rating(client_id)
    with tabs[4]:
        _render_business_plan(client_id)


def render_email(cfg: Any, hooks: Hooks) -> None:
    _section("Email e acquisizione allegati")
    labels = ["Download operativo", "Account", "Mittenti e opzioni", "Test connessioni", "Salva configurazione"]
    tab_objects = st.tabs(labels)
    callbacks = [
        hooks.mail_download_renderer, hooks.accounts_renderer, hooks.config_renderer,
        hooks.connection_renderer, hooks.save_load_renderer,
    ]
    for tab, callback in zip(tab_objects, callbacks):
        with tab:
            if callback:
                callback(cfg)
            else:
                st.info("Modulo non disponibile in questa installazione.")


def render_deadlines() -> None:
    _section("Scadenzario operativo")
    tab_list, tab_new, tab_close = st.tabs(["Elenco", "Nuova scadenza", "Aggiorna stato"])
    with tab_list:
        mode = st.radio("Vista", ["Aperte", "Oggi", "Scadute", "Tutte"], horizontal=True)
        _show_dataframe(
            db.list_deadlines(mode),
            {"due_on": "Data", "client_name": "Cliente", "title": "Attività", "priority": "Priorità", "status": "Stato", "notes": "Note"},
        )
    with tab_new:
        client_id = _client_select("Cliente (facoltativo)", "deadline_client", allow_empty=True)
        with st.form("new_deadline", clear_on_submit=True):
            title = st.text_input("Attività *")
            c1, c2, c3 = st.columns(3)
            due_on = c1.date_input("Scadenza *", value=date.today())
            priority = c2.selectbox("Priorità", ["Alta", "Media", "Bassa"], index=1)
            status = c3.selectbox("Stato", ["Da fare", "In corso", "In attesa", "Completata"])
            notes = st.text_area("Note")
            submitted = st.form_submit_button("Salva scadenza", type="primary")
        if submitted:
            try:
                db.save_deadline(
                    {"client_id": client_id, "title": title, "due_on": due_on, "priority": priority, "status": status, "notes": notes}
                )
                st.success("Scadenza registrata.")
            except Exception as exc:
                st.error(str(exc))
    with tab_close:
        rows = db.list_deadlines("Tutte")
        if rows:
            labels = {row["id"]: f"{row['due_on']} — {row['title']} — {row['client_name']}" for row in rows}
            deadline_id = st.selectbox("Scadenza", list(labels), format_func=lambda value: labels[value])
            status = st.selectbox("Nuovo stato", ["Da fare", "In corso", "In attesa", "Completata"], key="deadline_new_status")
            if st.button("Aggiorna stato", type="primary"):
                db.update_deadline_status(deadline_id, status)
                st.success("Stato aggiornato.")
                st.rerun()
        else:
            st.info("Nessuna scadenza registrata.")


def render_reports() -> None:
    _section("Reportistica professionale")
    client_id = _client_select("Cliente", "report_client")
    if not client_id:
        return
    client = db.get_client(client_id)
    financials = db.list_financials(client_id)
    risks = db.list_credit_risk(client_id)
    practices = db.list_practices(client_id)
    documents = db.list_documents(client_id)
    missing = db.missing_document_categories(client_id)
    rating = None
    if financials:
        rating = score_rating(financial_kpis(financials[-1]), risks[-1] if risks else None)
    st.write(
        f"Il dossier includerà {len(financials)} esercizi, {len(risks)} rilevazioni CR, "
        f"{len(practices)} pratiche e {len(documents)} documenti."
    )
    if missing:
        st.warning("Categorie essenziali mancanti: " + ", ".join(missing))
    if st.button("Genera dossier bancario PDF", type="primary"):
        try:
            pdf = build_bank_dossier(client, financials, risks, practices, documents, rating, missing)
            st.session_state["generated_dossier"] = pdf
            st.session_state["generated_dossier_name"] = safe_pdf_filename(client["name"])
            st.success("Dossier generato.")
        except Exception as exc:
            st.error(f"Generazione non riuscita: {exc}")
    if st.session_state.get("generated_dossier"):
        st.download_button(
            "Scarica dossier PDF",
            st.session_state["generated_dossier"],
            file_name=st.session_state["generated_dossier_name"],
            mime="application/pdf",
            type="primary",
        )


def render_settings(cfg: Any, hooks: Hooks) -> None:
    _section("Impostazioni e diagnostica")
    tabs = st.tabs(["Sistema", "Airtable Live", "Email", "Automazioni", "Sicurezza e backup", "Diagnostica"])
    with tabs[0]:
        st.code(str(db.DB_PATH))
        st.caption("Percorso database. Su hosting cloud configurare FINANCEPLUS_DATA_DIR su storage persistente.")
        st.info("Le credenziali non devono essere inserite nel repository: usare Streamlit Secrets o variabili d'ambiente.")
    with tabs[1]:
        if hooks.airtable_renderer:
            hooks.airtable_renderer()
        else:
            st.info("Modulo Airtable non disponibile.")
    with tabs[2]:
        if hooks.accounts_renderer:
            hooks.accounts_renderer(cfg)
        else:
            st.info("Modulo email non disponibile.")
    with tabs[3]:
        rows = db.list_automations()
        _show_dataframe(
            rows,
            {
                "name": "Automazione", "source": "Fonte", "cadence": "Frequenza", "filter_rule": "Filtro",
                "status": "Stato", "last_run": "Ultima esecuzione", "last_result": "Ultimo esito",
            },
        )
        with st.expander("Registra nuova automazione", expanded=not rows):
            with st.form("new_automation", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                name = c1.text_input("Nome *")
                source = c2.selectbox("Fonte *", ["Gmail", "Aruba IMAP", "Airtable", "Albo pretorio", "GitHub", "Altro"])
                cadence = c3.selectbox("Frequenza", ["Manuale", "Giornaliera", "Settimanale", "Mensile", "Su evento"])
                filter_rule = st.text_input("Filtro / condizione")
                status = st.selectbox("Stato", ["Da configurare", "Da verificare", "Attiva", "Sospesa"])
                notes = st.text_area("Note")
                submitted = st.form_submit_button("Registra automazione", type="primary")
            if submitted:
                try:
                    db.save_automation(
                        {"name": name, "source": source, "cadence": cadence, "filter_rule": filter_rule, "status": status, "notes": notes}
                    )
                    st.success("Automazione registrata. L'attivazione richiede un test effettivo della fonte.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        st.caption("La registrazione documenta la regola; l'esecuzione pianificata va attivata nel servizio di automazione scelto.")
    with tabs[4]:
        password_configured = bool(os.getenv("FINANCEPLUS_APP_PASSWORD"))
        st.metric("Protezione accesso", "Configurata" if password_configured else "Non configurata")
        st.caption("Impostare FINANCEPLUS_APP_PASSWORD in Streamlit Secrets o nelle variabili d'ambiente.")
        try:
            backup = db.backup_bytes()
            st.download_button(
                "Scarica backup completo ZIP", backup,
                file_name=f"FINANCE_PLUS_GOLD_GENERALE_BACKUP_{date.today():%Y%m%d}.zip",
                mime="application/zip", type="primary",
            )
        except Exception as exc:
            st.error(f"Backup non disponibile: {exc}")
        st.subheader("Audit log")
        _show_dataframe(
            db.list_audit_log(),
            {"event_time": "Data/ora", "action": "Azione", "entity_type": "Entità", "entity_id": "ID", "detail": "Dettaglio"},
        )
    with tabs[5]:
        if st.button("Esegui diagnostica", type="primary"):
            checks: List[Dict[str, str]] = []
            try:
                db.init_db()
                with db.connection() as conn:
                    conn.execute("SELECT 1").fetchone()
                checks.append({"Componente": "Database SQLite", "Stato": "OK", "Dettaglio": str(db.DB_PATH)})
            except (OSError, sqlite3.Error) as exc:
                checks.append({"Componente": "Database SQLite", "Stato": "ERRORE", "Dettaglio": str(exc)})
            try:
                db.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
                writable = os.access(db.DOCUMENTS_DIR, os.W_OK)
                checks.append({"Componente": "Archivio documenti", "Stato": "OK" if writable else "ERRORE", "Dettaglio": str(db.DOCUMENTS_DIR)})
            except OSError as exc:
                checks.append({"Componente": "Archivio documenti", "Stato": "ERRORE", "Dettaglio": str(exc)})
            checks.append(
                {
                    "Componente": "Airtable Secrets", "Stato": "CONFIGURATO" if os.getenv("AIRTABLE_TOKEN") else "DA VERIFICARE",
                    "Dettaglio": "Il test live è disponibile nella scheda Airtable Live.",
                }
            )
            st.dataframe(checks, use_container_width=True, hide_index=True)


def render_workspace(cfg: Any = None, hooks: Optional[Hooks] = None) -> None:
    db.init_db()
    hooks = hooks or Hooks()
    _style()
    _header()
    page = st.radio("Navigazione principale", PAGES, horizontal=True, label_visibility="collapsed", key="gold_page")
    st.caption("Le analisi sono calcolate sui dati salvati; nessun dato dimostrativo viene presentato come reale.")
    if page == "Dashboard":
        render_dashboard()
    elif page == "Clienti":
        render_clients()
    elif page == "Pratiche":
        render_practices()
    elif page == "Documenti":
        render_documents()
    elif page == "Analisi":
        render_analysis()
    elif page == "Mandati":
        render_mandates()
    elif page == "Banche":
        render_banks()
    elif page == "Email":
        render_email(cfg, hooks)
    elif page == "Scadenzario":
        render_deadlines()
    elif page == "Report":
        render_reports()
    else:
        render_settings(cfg, hooks)
