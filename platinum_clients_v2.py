from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Mapping

import streamlit as st

import platinum_clients as base
from platinum_pdf import build_document_summary_pdf, safe_pdf_filename


def _document_rows(token: str, base_id: str, document_ids: List[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for rid in document_ids:
        try:
            rec = base._cached_record(token, base_id, base.TABLES["Documenti"], rid)
            fields: Mapping[str, Any] = rec.get("fields", {})
        except Exception:
            continue
        row: Dict[str, Any] = {}
        for label, field_id in base.DOCUMENT_FIELDS.items():
            row[label] = base._as_text(base._value(fields, field_id))
        rows.append(row)

    def _sort_key(item: Mapping[str, Any]) -> tuple[str, str, str]:
        return (
            str(item.get("Tipo Documento") or ""),
            str(item.get("Esercizio") or ""),
            str(item.get("Data Documento") or ""),
        )

    rows.sort(key=_sort_key)
    return rows


def _csv_bytes(rows: List[Dict[str, Any]]) -> bytes:
    output = io.StringIO()
    columns = [
        "Tipo Documento",
        "Esercizio",
        "Data Documento",
        "Nome Definitivo",
        "Nome Originale",
        "Origine",
        "Stato Verifica",
        "Sintesi IA",
        "URL Drive",
    ]
    writer = csv.DictWriter(output, fieldnames=columns, delimiter=";", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")


def _render_document_summary_for_selected_client() -> None:
    selected_id = st.session_state.get("platinum_selected_client")
    if not selected_id:
        return

    token, base_id = base.airtable_config()
    if not token:
        return

    try:
        client = base._cached_record(token, base_id, base.TABLES["Clienti"], selected_id)
    except Exception as exc:
        st.warning(f"Riepilogo documenti non disponibile: {exc}")
        return

    fields = client.get("fields", {})
    name = base._as_text(base._value(fields, base.CLIENT_FIELDS["name"])) or "Cliente"
    vat = base._as_text(base._value(fields, base.CLIENT_FIELDS["vat"])) or "-"
    tax_code = base._as_text(base._value(fields, base.CLIENT_FIELDS["tax_code"])) or "-"
    rating = base._as_text(base._value(fields, base.CLIENT_FIELDS["rating"])) or "N/D"
    document_ids = list(base._value(fields, base.CLIENT_FIELDS["documents"], []) or [])

    st.markdown("---")
    st.subheader("📚 Riepilogo documenti cliente")
    st.caption(
        "Visualizza in forma tabellare tutti i documenti collegati al cliente in Airtable e genera il PDF riepilogativo."
    )

    if not document_ids:
        st.info("Per questo cliente non risultano documenti collegati in Airtable.")
        return

    session_key = f"platinum_show_doc_summary_{selected_id}"
    c1, c2 = st.columns([1, 1])
    if c1.button(
        "📋 Visualizza riepilogo documenti",
        key=f"btn_show_docs_{selected_id}",
        use_container_width=True,
    ):
        st.session_state[session_key] = not bool(st.session_state.get(session_key, False))

    try:
        with st.spinner("Preparazione riepilogo documentale..."):
            rows = _document_rows(token, base_id, document_ids)
    except Exception as exc:
        st.error(f"Errore nella lettura dei documenti: {exc}")
        return

    if not rows:
        st.warning("I collegamenti ai documenti esistono, ma i record non sono leggibili con le credenziali Airtable configurate.")
        return

    pdf_bytes = build_document_summary_pdf(
        client_name=name,
        vat_number=vat,
        tax_code=tax_code,
        rating=rating,
        documents=rows,
    )

    c2.download_button(
        "📄 Scarica riepilogo PDF",
        data=pdf_bytes,
        file_name=safe_pdf_filename(name),
        mime="application/pdf",
        key=f"btn_pdf_docs_{selected_id}",
        use_container_width=True,
    )

    st.caption(f"Documenti inclusi nel riepilogo: **{len(rows)}**")

    if st.session_state.get(session_key, False):
        display_rows = []
        for idx, row in enumerate(rows, start=1):
            display_rows.append(
                {
                    "N.": idx,
                    "Tipo": row.get("Tipo Documento") or "-",
                    "Esercizio": row.get("Esercizio") or "-",
                    "Data": row.get("Data Documento") or "-",
                    "Documento": row.get("Nome Definitivo") or row.get("Nome Originale") or row.get("Documento") or "-",
                    "Origine": row.get("Origine") or "-",
                    "Stato": row.get("Stato Verifica") or "-",
                    "Sintesi": row.get("Sintesi IA") or "-",
                    "Drive": row.get("URL Drive") or "-",
                }
            )
        st.dataframe(display_rows, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Scarica anche tabella CSV",
            data=_csv_bytes(rows),
            file_name=safe_pdf_filename(name).replace(".pdf", ".csv"),
            mime="text/csv",
            key=f"btn_csv_docs_{selected_id}",
        )


def render_clients_section() -> None:
    base.render_clients_section()
    _render_document_summary_for_selected_client()
