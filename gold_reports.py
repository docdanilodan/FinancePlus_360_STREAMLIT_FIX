"""Report PDF professionali per FINANCE_PLUS_GOLD_GENERALE."""

from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO
from typing import Any, Mapping, Optional, Sequence
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from gold_analytics import RatingResult, central_risk_kpis, financial_kpis


NAVY = colors.HexColor("#073F73")
BLUE = colors.HexColor("#155A93")
COPPER = colors.HexColor("#B87333")
PALE_BLUE = colors.HexColor("#EDF5FB")
LIGHT = colors.HexColor("#F5F7FA")
INK = colors.HexColor("#26394A")
MUTED = colors.HexColor("#687B8B")


def _money(value: Any) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        return "—"
    return (f"€ {amount:,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")


def _ratio(value: Any, suffix: str = "x") -> str:
    if value is None:
        return "N/D"
    try:
        return f"{float(value):.2f}{suffix}"
    except (TypeError, ValueError):
        return "N/D"


def _percent(value: Any) -> str:
    if value is None:
        return "N/D"
    try:
        return f"{float(value):.1%}"
    except (TypeError, ValueError):
        return "N/D"


def safe_pdf_filename(name: str, suffix: str = "Dossier_Bancario") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "Cliente"
    return f"{cleaned}_{suffix}_{datetime.now():%Y%m%d}.pdf"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleFP", parent=base["Title"], fontName="Helvetica-Bold", fontSize=22,
            leading=27, textColor=NAVY, alignment=TA_CENTER, spaceAfter=8 * mm,
        ),
        "subtitle": ParagraphStyle(
            "SubtitleFP", parent=base["Normal"], fontSize=11, leading=15,
            textColor=MUTED, alignment=TA_CENTER, spaceAfter=4 * mm,
        ),
        "h1": ParagraphStyle(
            "H1FP", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=14,
            leading=18, textColor=NAVY, spaceBefore=4 * mm, spaceAfter=3 * mm,
        ),
        "h2": ParagraphStyle(
            "H2FP", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11,
            leading=14, textColor=BLUE, spaceBefore=3 * mm, spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "BodyFP", parent=base["BodyText"], fontSize=9, leading=13,
            textColor=INK, alignment=TA_LEFT, spaceAfter=2 * mm,
        ),
        "small": ParagraphStyle(
            "SmallFP", parent=base["BodyText"], fontSize=7.5, leading=10, textColor=MUTED,
        ),
        "white": ParagraphStyle(
            "WhiteFP", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8,
            leading=10, textColor=colors.white,
        ),
    }


def _p(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(value if value not in (None, "") else "—")), style)


def _table(
    rows: Sequence[Sequence[Any]],
    styles: Mapping[str, ParagraphStyle],
    widths: Optional[Sequence[float]] = None,
    header: bool = True,
) -> Table:
    prepared = []
    for row_index, row in enumerate(rows):
        style = styles["white"] if header and row_index == 0 else styles["body"]
        prepared.append([_p(value, style) for value in row])
    table = Table(prepared, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D5E0E8")),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, LIGHT]),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    table.setStyle(TableStyle(commands))
    return table


def _header_footer(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 11 * mm, width, 11 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(16 * mm, height - 7 * mm, "FINANCE_PLUS_GOLD_GENERALE")
    canvas.setStrokeColor(COPPER)
    canvas.setLineWidth(1.2)
    canvas.line(16 * mm, 12 * mm, width - 16 * mm, 12 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(16 * mm, 7.5 * mm, "Documento gestionale riservato — dati da verificare con le fonti ufficiali")
    canvas.drawRightString(width - 16 * mm, 7.5 * mm, f"Pagina {doc.page}")
    canvas.restoreState()


def build_bank_dossier(
    client: Mapping[str, Any],
    financials: Sequence[Mapping[str, Any]],
    credit_risk: Sequence[Mapping[str, Any]],
    practices: Sequence[Mapping[str, Any]],
    documents: Sequence[Mapping[str, Any]],
    rating: Optional[RatingResult],
    missing_documents: Sequence[str],
) -> bytes:
    buffer = BytesIO()
    styles = _styles()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=19 * mm,
        bottomMargin=17 * mm,
        title=f"Dossier bancario - {client.get('name', 'Cliente')}",
        author="FINANCE_PLUS_GOLD_GENERALE",
    )
    story: list[Any] = []
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("FINANCE_PLUS_GOLD_GENERALE", styles["title"]))
    story.append(Paragraph("Dossier bancario e analisi economico-finanziaria", styles["subtitle"]))
    story.append(Spacer(1, 8 * mm))
    client_box = Table(
        [
            [_p("CLIENTE", styles["white"])],
            [_p(client.get("name"), styles["h1"])],
            [_p(f"P.IVA: {client.get('vat') or '—'}   |   C.F.: {client.get('tax_code') or '—'}", styles["body"])],
            [_p(f"Sede: {client.get('legal_address') or '—'}", styles["body"])],
        ],
        colWidths=[178 * mm],
    )
    client_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("BOX", (0, 0), (-1, -1), 0.8, NAVY),
                ("BACKGROUND", (0, 1), (-1, -1), PALE_BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(client_box)
    story.append(Spacer(1, 9 * mm))
    story.append(
        Paragraph(
            f"Generato il {datetime.now():%d/%m/%Y alle %H:%M}. Il documento elabora esclusivamente i dati "
            "registrati nell'applicazione e non sostituisce la valutazione dell'istituto finanziatore.",
            styles["small"],
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("1. Executive Summary", styles["h1"]))
    latest_financial = financials[-1] if financials else None
    latest_cr = credit_risk[-1] if credit_risk else None
    kpis = financial_kpis(latest_financial) if latest_financial else {}
    cr_kpis = central_risk_kpis(latest_cr)
    summary_rows = [
        ["Indicatore", "Valore", "Lettura"],
        ["Rating gestionale", rating.rating if rating else "N/D", rating.judgement if rating else "Dati insufficienti"],
        ["Score", f"{rating.score}/100" if rating else "N/D", f"PD indicativa {rating.pd_range}" if rating else "—"],
        ["Ricavi ultimo esercizio", _money(kpis.get("revenue")), str(latest_financial.get("fiscal_year")) if latest_financial else "—"],
        ["EBITDA margin", _percent(kpis.get("ebitda_margin")), "Redditività operativa"],
        ["PFN/EBITDA", _ratio(kpis.get("pfn_ebitda")), "Indebitamento finanziario"],
        ["DSCR", _ratio(kpis.get("dscr")), "Copertura del servizio del debito"],
        ["Utilizzo affidamenti", _percent(cr_kpis.get("utilization")), "Ultima CR registrata"],
    ]
    story.append(_table(summary_rows, styles, [55 * mm, 40 * mm, 83 * mm]))

    if rating:
        story.append(Paragraph("Punti di forza", styles["h2"]))
        story.append(Paragraph("<br/>".join(f"• {escape(item)}" for item in rating.strengths) or "Nessuno rilevato.", styles["body"]))
        story.append(Paragraph("Criticità", styles["h2"]))
        story.append(Paragraph("<br/>".join(f"• {escape(item)}" for item in rating.weaknesses) or "Nessuna rilevata.", styles["body"]))

    story.append(Paragraph("2. Profilo aziendale", styles["h1"]))
    profile_rows = [
        ["Dato", "Valore"],
        ["Denominazione", client.get("name") or "—"],
        ["Forma giuridica", client.get("legal_form") or "—"],
        ["P.IVA", client.get("vat") or "—"],
        ["Codice fiscale", client.get("tax_code") or "—"],
        ["REA", client.get("rea") or "—"],
        ["ATECO", client.get("ateco") or "—"],
        ["Amministratore", client.get("administrator") or "—"],
        ["PEC", client.get("pec") or "—"],
        ["Responsabile pratica", client.get("manager") or "—"],
    ]
    story.append(_table(profile_rows, styles, [55 * mm, 123 * mm]))

    story.append(Paragraph("3. Andamento economico-finanziario", styles["h1"]))
    if financials:
        rows = [["Anno", "Ricavi", "EBITDA", "EBITDA %", "PFN", "PFN/EBITDA", "DSCR"]]
        for row in financials:
            item = financial_kpis(row)
            rows.append(
                [
                    row.get("fiscal_year"), _money(item["revenue"]), _money(item["ebitda"]),
                    _percent(item["ebitda_margin"]), _money(item["pfn"]),
                    _ratio(item["pfn_ebitda"]), _ratio(item["dscr"]),
                ]
            )
        story.append(_table(rows, styles, [15 * mm, 31 * mm, 28 * mm, 25 * mm, 29 * mm, 27 * mm, 23 * mm]))
    else:
        story.append(Paragraph("Non risultano dati di bilancio registrati.", styles["body"]))

    story.append(Paragraph("4. Centrale Rischi", styles["h1"]))
    if credit_risk:
        rows = [["Data", "Accordato", "Utilizzato", "Utilizzo", "Scaduto", "Past due", "Banche"]]
        for row in credit_risk:
            item = central_risk_kpis(row)
            rows.append(
                [
                    row.get("reference_date"), _money(item["granted"]), _money(item["utilized"]),
                    _percent(item["utilization"]), _money(item["overdue"]), _money(item["past_due"]),
                    row.get("number_banks") or 0,
                ]
            )
        story.append(_table(rows, styles, [22 * mm, 29 * mm, 29 * mm, 24 * mm, 27 * mm, 27 * mm, 20 * mm]))
    else:
        story.append(Paragraph("Non risultano dati di Centrale Rischi registrati.", styles["body"]))

    story.append(Paragraph("5. Pratiche finanziarie", styles["h1"]))
    if practices:
        rows = [["Tipo", "Istituto", "Richiesto", "Stato", "Probabilità", "Prossima azione"]]
        for row in practices:
            rows.append(
                [
                    row.get("practice_type"), row.get("institution") or "—", _money(row.get("amount_requested")),
                    row.get("status"), f"{float(row.get('probability') or 0):.0f}%", row.get("next_action") or "—",
                ]
            )
        story.append(_table(rows, styles, [31 * mm, 27 * mm, 29 * mm, 27 * mm, 24 * mm, 40 * mm]))
    else:
        story.append(Paragraph("Non risultano pratiche finanziarie registrate.", styles["body"]))

    story.append(Paragraph("6. Completezza documentale", styles["h1"]))
    story.append(
        Paragraph(
            f"Documenti archiviati: <b>{len(documents)}</b>. "
            f"Categorie essenziali mancanti: <b>{', '.join(escape(x) for x in missing_documents) if missing_documents else 'nessuna'}</b>.",
            styles["body"],
        )
    )
    if documents:
        rows = [["Documento", "Categoria", "Data", "Verifica"]]
        for row in documents[:40]:
            rows.append(
                [row.get("original_name"), row.get("category"), row.get("document_date") or "—", row.get("verification_status")]
            )
        story.append(_table(rows, styles, [83 * mm, 36 * mm, 27 * mm, 32 * mm]))

    story.append(Paragraph("7. Avvertenze metodologiche", styles["h1"]))
    story.append(
        Paragraph(
            "Lo score è un indicatore gestionale interno basato sui dati inseriti e su soglie trasparenti. "
            "Non riproduce il modello proprietario di MCC, CRIF o di una banca e non costituisce promessa di credito. "
            "Prima dell'utilizzo esterno occorre riconciliare bilanci, Centrale Rischi, estratti conto e documentazione ufficiale.",
            styles["body"],
        )
    )

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()
