from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO
from typing import Any, Mapping, Sequence
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


NAVY = colors.HexColor("#12304A")
COPPER = colors.HexColor("#B87333")
LIGHT_HEADER = colors.HexColor("#EAF0F5")
LIGHT_ROW = colors.HexColor("#F7F9FB")
GRID = colors.HexColor("#C9D2DA")
TEXT = colors.HexColor("#1F2933")
MUTED = colors.HexColor("#5F6B76")


def safe_pdf_filename(client_name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", (client_name or "Cliente").strip())
    value = re.sub(r"_+", "_", value).strip("_.") or "Cliente"
    return f"Riepilogo_Documenti_{value}.pdf"


def _txt(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    value = str(value).strip()
    return value if value else default


def _paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_txt(value)), style)


def _link_paragraph(url: Any, style: ParagraphStyle) -> Paragraph:
    url_text = _txt(url, "")
    if not url_text:
        return Paragraph("-", style)
    safe_url = escape(url_text, {'"': '&quot;'})
    return Paragraph(f'<link href="{safe_url}" color="#12304A"><u>Apri Drive</u></link>', style)


def build_document_summary_pdf(
    client_name: str,
    vat_number: str,
    tax_code: str,
    rating: str,
    documents: Sequence[Mapping[str, Any]],
) -> bytes:
    """Genera un riepilogo PDF tabellare di tutti i documenti collegati al cliente."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=11 * mm,
        bottomMargin=11 * mm,
        title=f"Riepilogo documenti - {client_name}",
        author="FinancePlus PLATINUM",
        subject="Riepilogo documentale cliente",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FPTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=NAVY,
        alignment=TA_LEFT,
        spaceAfter=4 * mm,
    )
    meta_style = ParagraphStyle(
        "FPMeta",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=MUTED,
        alignment=TA_LEFT,
    )
    cell_style = ParagraphStyle(
        "FPCell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=6.9,
        leading=8.7,
        textColor=TEXT,
        alignment=TA_LEFT,
    )
    cell_center = ParagraphStyle(
        "FPCellCenter",
        parent=cell_style,
        alignment=TA_CENTER,
    )
    header_style = ParagraphStyle(
        "FPHeader",
        parent=cell_style,
        fontName="Helvetica-Bold",
        fontSize=7.0,
        leading=8.8,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    note_style = ParagraphStyle(
        "FPNote",
        parent=styles["BodyText"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=9.5,
        textColor=MUTED,
    )

    story = [
        Paragraph("FINANCEPLUS PLATINUM - RIEPILOGO DOCUMENTALE", title_style),
        Paragraph(
            f"<b>Cliente:</b> {escape(_txt(client_name))} &nbsp;&nbsp; "
            f"<b>P.IVA:</b> {escape(_txt(vat_number))} &nbsp;&nbsp; "
            f"<b>Codice fiscale:</b> {escape(_txt(tax_code))} &nbsp;&nbsp; "
            f"<b>Rating:</b> {escape(_txt(rating, 'N/D'))}",
            meta_style,
        ),
        Paragraph(
            f"Documenti collegati in Airtable: <b>{len(documents)}</b> &nbsp;&nbsp; "
            f"Generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            meta_style,
        ),
        Spacer(1, 4 * mm),
    ]

    headers = [
        "N.",
        "Tipo",
        "Esercizio",
        "Data",
        "Nome documento",
        "Origine",
        "Stato",
        "Sintesi",
        "Link",
    ]
    data = [[Paragraph(h, header_style) for h in headers]]

    for idx, row in enumerate(documents, start=1):
        document_name = (
            row.get("Nome Definitivo")
            or row.get("Nome Originale")
            or row.get("Documento")
            or "-"
        )
        data.append(
            [
                Paragraph(str(idx), cell_center),
                _paragraph(row.get("Tipo Documento"), cell_style),
                _paragraph(row.get("Esercizio"), cell_center),
                _paragraph(row.get("Data Documento"), cell_center),
                _paragraph(document_name, cell_style),
                _paragraph(row.get("Origine"), cell_center),
                _paragraph(row.get("Stato Verifica"), cell_center),
                _paragraph(row.get("Sintesi IA"), cell_style),
                _link_paragraph(row.get("URL Drive"), cell_center),
            ]
        )

    col_widths = [
        8 * mm,
        25 * mm,
        16 * mm,
        20 * mm,
        50 * mm,
        19 * mm,
        23 * mm,
        91 * mm,
        20 * mm,
    ]

    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (3, -1), "CENTER"),
        ("ALIGN", (5, 1), (6, -1), "CENTER"),
        ("ALIGN", (8, 1), (8, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("BOX", (0, 0), (-1, -1), 0.6, NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, 0), 1.4, COPPER),
    ]
    for row_index in range(1, len(data)):
        if row_index % 2 == 0:
            style_commands.append(("BACKGROUND", (0, row_index), (-1, row_index), LIGHT_ROW))
    table.setStyle(TableStyle(style_commands))
    story.append(table)
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            "Il riepilogo riporta i record documentali collegati al cliente in Airtable al momento della generazione. "
            "Il link Drive e' mostrato solo quando presente nel record.",
            note_style,
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
