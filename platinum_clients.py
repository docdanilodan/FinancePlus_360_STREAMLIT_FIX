from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from urllib.parse import quote

import requests
import streamlit as st

AIRTABLE_BASE_ID_DEFAULT = ""

TABLES = {
    "Clienti": "Clienti",
    "Pratiche": "Pratiche",
    "Documenti": "Documenti",
    "Email": "Email",
    "Analisi Creditizie": "Analisi Creditizie",
}

CLIENT_FIELDS = {
    "name": "Denominazione",
    "vat": "Partita IVA",
    "tax_code": "Codice Fiscale",
    "pec": "PEC",
    "email": "Email",
    "status": "Stato Cliente",
    "drive": "Cartella Drive",
    "notes": "Note",
    "practices": "Pratiche",
    "documents": "Documenti",
    "emails": "Email collegate",
    "analyses": "Analisi Creditizie",
    "rating_date": "Data ultimo rating",
    "last_balance": "Ultimo bilancio disponibile",
    "rating": "Rating corrente",
}

PRACTICE_FIELDS = {name: name for name in (
    "Pratica ID", "Tipo Pratica", "Istituto", "Importo Richiesto", "Stato", "Priorita",
    "Data Apertura", "Scadenza", "Responsabile", "Prossima azione", "Completezza dossier",
    "Probabilita delibera", "Importo massimo stimato", "Alert e criticita", "Documenti mancanti",
)}

DOCUMENT_FIELDS = {name: name for name in (
    "Documento", "Tipo Documento", "Esercizio", "Data Documento", "Nome Originale",
    "Nome Definitivo", "Origine", "URL Drive", "Sintesi IA", "Stato Verifica",
)}

EMAIL_FIELDS = {name: name for name in (
    "Oggetto", "Data e ora", "Mittente", "Sintesi IA", "Allegati", "Priorita",
    "Azione Richiesta", "Gestita",
)}

ANALYSIS_FIELDS = {name: name for name in (
    "Analisi ID", "Data Analisi", "Esercizio", "Ricavi", "EBITDA", "EBITDA Margin", "PFN",
    "PFN EBITDA", "DSCR", "Patrimonio Netto", "Score", "Rating", "Importo Sostenibile Min",
    "Importo Sostenibile Max", "Punti di Forza", "Criticita", "Raccomandazione IA",
)}


def _secret(name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        if name in st.secrets:
            value = st.secrets[name]
            return str(value) if value is not None else default
    except Exception:
        pass
    return os.getenv(name, default)


def airtable_config() -> tuple[Optional[str], str]:
    token = _secret("AIRTABLE_TOKEN")
    base_id = _secret("AIRTABLE_BASE_ID", AIRTABLE_BASE_ID_DEFAULT) or AIRTABLE_BASE_ID_DEFAULT
    return token, base_id


class AirtableAPIError(RuntimeError):
    pass


class AirtableClient:
    def __init__(self, token: str, base_id: str):
        self.token = token
        self.base_id = base_id
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _url(self, table_id: str, record_id: Optional[str] = None) -> str:
        base = f"https://api.airtable.com/v0/{self.base_id}/{quote(table_id, safe='')}"
        return f"{base}/{record_id}" if record_id else base

    def list_records(self, table_id: str, field_ids: Sequence[str] = ()) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        params: List[tuple[str, str]] = [("pageSize", "100"), ("returnFieldsByFieldId", "true")]
        params.extend(("fields[]", fid) for fid in field_ids)
        offset: Optional[str] = None
        while True:
            request_params = list(params)
            if offset:
                request_params.append(("offset", offset))
            resp = self.session.get(self._url(table_id), params=request_params, timeout=25)
            if not resp.ok:
                raise AirtableAPIError(f"Airtable HTTP {resp.status_code}: {resp.text[:300]}")
            payload = resp.json()
            records.extend(payload.get("records", []))
            offset = payload.get("offset")
            if not offset:
                break
        return records

    def get_record(self, table_id: str, record_id: str) -> Dict[str, Any]:
        resp = self.session.get(
            self._url(table_id, record_id),
            params={"returnFieldsByFieldId": "true"},
            timeout=25,
        )
        if not resp.ok:
            raise AirtableAPIError(f"Airtable HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()


@st.cache_data(ttl=120, show_spinner=False)
def _cached_clients(token: str, base_id: str) -> List[Dict[str, Any]]:
    api = AirtableClient(token, base_id)
    return api.list_records(TABLES["Clienti"], list(CLIENT_FIELDS.values()))


@st.cache_data(ttl=120, show_spinner=False)
def _cached_record(token: str, base_id: str, table_id: str, record_id: str) -> Dict[str, Any]:
    return AirtableClient(token, base_id).get_record(table_id, record_id)


def _value(fields: Mapping[str, Any], field_id: str, default: Any = "") -> Any:
    value = fields.get(field_id, default)
    if isinstance(value, dict):
        return value.get("name") or value.get("value") or str(value)
    return value


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Si" if value else "No"
    if isinstance(value, (list, tuple)):
        return ", ".join(_as_text(v) for v in value)
    if isinstance(value, dict):
        return str(value.get("name") or value.get("value") or value)
    return str(value)


def _fmt_number(value: Any) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return _as_text(value) or "-"
    return f"EUR {n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _searchable_client(record: Mapping[str, Any]) -> str:
    f = record.get("fields", {})
    parts = [
        _value(f, CLIENT_FIELDS["name"]),
        _value(f, CLIENT_FIELDS["vat"]),
        _value(f, CLIENT_FIELDS["tax_code"]),
        _value(f, CLIENT_FIELDS["pec"]),
        _value(f, CLIENT_FIELDS["email"]),
    ]
    return " ".join(_as_text(x) for x in parts).lower()


def _client_label(record: Mapping[str, Any]) -> str:
    f = record.get("fields", {})
    name = _as_text(_value(f, CLIENT_FIELDS["name"])) or "Cliente senza nome"
    vat = _as_text(_value(f, CLIENT_FIELDS["vat"]))
    return f"{name}  |  P.IVA {vat}" if vat else name


def _render_pairs(fields: Mapping[str, Any], mapping: Mapping[str, str], money_fields: Iterable[str] = ()) -> None:
    money = set(money_fields)
    rows = []
    for label, fid in mapping.items():
        if fid not in fields:
            continue
        raw = _value(fields, fid)
        if raw in (None, "", [], {}):
            continue
        shown = _fmt_number(raw) if label in money else _as_text(raw)
        rows.append({"Campo": label, "Valore": shown})
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun dato disponibile per questa sezione.")


def _render_related_records(
    token: str,
    base_id: str,
    table_id: str,
    record_ids: Sequence[str],
    mapping: Mapping[str, str],
    money_fields: Iterable[str] = (),
) -> None:
    if not record_ids:
        st.info("Nessun record collegato.")
        return
    for i, rid in enumerate(record_ids, start=1):
        try:
            rec = _cached_record(token, base_id, table_id, rid)
            fields = rec.get("fields", {})
        except Exception as exc:
            st.warning(f"Record {rid}: {exc}")
            continue
        first_value = ""
        for fid in mapping.values():
            if fid in fields:
                first_value = _as_text(_value(fields, fid))
                if first_value:
                    break
        title = first_value or f"Record {i}"
        with st.expander(title, expanded=i == 1):
            _render_pairs(fields, mapping, money_fields=money_fields)


def render_clients_section() -> None:
    st.header("👥 Clienti")
    st.caption("Anagrafica FinancePlus collegata in tempo reale ad Airtable. Ricerca e consultazione senza uscire da Streamlit.")

    token, base_id = airtable_config()
    if not token:
        st.error("Collegamento Airtable non configurato.")
        st.info(
            "In Streamlit Cloud apri App settings → Secrets e aggiungi:\n\n"
            'AIRTABLE_TOKEN = "pat_..."\n'
            f'AIRTABLE_BASE_ID = "{AIRTABLE_BASE_ID_DEFAULT}"'
        )
        return

    top1, top2 = st.columns([4, 1])
    query = top1.text_input(
        "Cerca cliente",
        placeholder="Ragione sociale, P.IVA, codice fiscale, PEC o email...",
        key="platinum_client_search",
    )
    if top2.button("Aggiorna Airtable", use_container_width=True):
        _cached_clients.clear()
        _cached_record.clear()
        st.rerun()

    try:
        with st.spinner("Lettura anagrafiche Airtable..."):
            all_clients = _cached_clients(token, base_id)
    except Exception as exc:
        st.error(f"Impossibile leggere Airtable: {exc}")
        return

    q = query.strip().lower()
    filtered = [r for r in all_clients if not q or q in _searchable_client(r)]
    filtered.sort(key=lambda r: _client_label(r).lower())

    c1, c2, c3 = st.columns(3)
    c1.metric("Clienti in Airtable", len(all_clients))
    c2.metric("Risultati ricerca", len(filtered))
    rated = sum(1 for r in all_clients if _value(r.get("fields", {}), CLIENT_FIELDS["rating"]))
    c3.metric("Clienti con rating", rated)

    if not filtered:
        st.warning("Nessun cliente corrisponde alla ricerca.")
        return

    selected_id = st.selectbox(
        "Apri anagrafica",
        options=[r["id"] for r in filtered],
        format_func=lambda rid: _client_label(next(r for r in filtered if r["id"] == rid)),
        key="platinum_selected_client",
    )
    selected = next(r for r in filtered if r["id"] == selected_id)
    f = selected.get("fields", {})

    name = _as_text(_value(f, CLIENT_FIELDS["name"])) or "Cliente"
    vat = _as_text(_value(f, CLIENT_FIELDS["vat"])) or "-"
    tax_code = _as_text(_value(f, CLIENT_FIELDS["tax_code"])) or "-"
    rating = _as_text(_value(f, CLIENT_FIELDS["rating"])) or "N/D"

    st.markdown(f"### {name}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("P.IVA", vat)
    m2.metric("Codice fiscale", tax_code)
    m3.metric("Rating FinancePlus", rating)
    m4.metric("Ultimo bilancio", _as_text(_value(f, CLIENT_FIELDS["last_balance"])) or "N/D")

    tab_a, tab_p, tab_d, tab_e, tab_r = st.tabs(
        ["Anagrafica", "Pratiche", "Documenti", "Email", "Analisi Creditizie"]
    )

    with tab_a:
        left, right = st.columns(2)
        with left:
            st.subheader("Dati identificativi")
            _render_pairs(
                f,
                {
                    "Ragione sociale": CLIENT_FIELDS["name"],
                    "Partita IVA": CLIENT_FIELDS["vat"],
                    "Codice Fiscale": CLIENT_FIELDS["tax_code"],
                    "PEC": CLIENT_FIELDS["pec"],
                    "Email": CLIENT_FIELDS["email"],
                    "Stato Cliente": CLIENT_FIELDS["status"],
                },
            )
        with right:
            st.subheader("Dossier e rating")
            _render_pairs(
                f,
                {
                    "Rating FinancePlus": CLIENT_FIELDS["rating"],
                    "Data ultimo rating": CLIENT_FIELDS["rating_date"],
                    "Ultimo bilancio disponibile": CLIENT_FIELDS["last_balance"],
                    "Cartella Drive": CLIENT_FIELDS["drive"],
                },
            )
        notes = _as_text(_value(f, CLIENT_FIELDS["notes"]))
        if notes:
            st.subheader("Note societarie / istruttorie")
            st.text_area("Note", value=notes, height=180, disabled=True, label_visibility="collapsed")

    with tab_p:
        _render_related_records(
            token,
            base_id,
            TABLES["Pratiche"],
            _value(f, CLIENT_FIELDS["practices"], []) or [],
            PRACTICE_FIELDS,
            money_fields={"Importo Richiesto", "Importo massimo stimato"},
        )

    with tab_d:
        _render_related_records(
            token,
            base_id,
            TABLES["Documenti"],
            _value(f, CLIENT_FIELDS["documents"], []) or [],
            DOCUMENT_FIELDS,
        )

    with tab_e:
        _render_related_records(
            token,
            base_id,
            TABLES["Email"],
            _value(f, CLIENT_FIELDS["emails"], []) or [],
            EMAIL_FIELDS,
        )

    with tab_r:
        _render_related_records(
            token,
            base_id,
            TABLES["Analisi Creditizie"],
            _value(f, CLIENT_FIELDS["analyses"], []) or [],
            ANALYSIS_FIELDS,
            money_fields={"Ricavi", "EBITDA", "PFN", "Patrimonio Netto", "Importo Sostenibile Min", "Importo Sostenibile Max"},
        )
