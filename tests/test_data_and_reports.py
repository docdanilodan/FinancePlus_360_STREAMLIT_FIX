from __future__ import annotations

from pathlib import Path

import gold_data as db
from gold_analytics import financial_kpis, score_rating
from gold_reports import build_bank_dossier


def _isolated_storage(tmp_path: Path) -> None:
    db.DATA_DIR = tmp_path / "data"
    db.DOCUMENTS_DIR = db.DATA_DIR / "documenti"
    db.DB_PATH = db.DATA_DIR / "test.sqlite3"
    db.init_db()


def test_client_document_and_financial_roundtrip(tmp_path: Path) -> None:
    _isolated_storage(tmp_path)
    client_id = db.save_client({"name": "Impresa Test", "vat": "", "tax_code": ""})
    client = db.get_client(client_id)
    assert client is not None
    assert client["name"] == "Impresa Test"
    assert client["vat"] == ""

    first_id, created = db.save_document(client_id, "bilancio.pdf", b"%PDF-test", "Bilancio", fiscal_year=2025)
    second_id, created_again = db.save_document(client_id, "copia.pdf", b"%PDF-test", "Bilancio", fiscal_year=2025)
    assert created is True
    assert created_again is False
    assert first_id == second_id

    db.save_financial(
        {
            "client_id": client_id,
            "fiscal_year": 2025,
            "revenue": 1_000_000,
            "ebitda": 150_000,
            "cash_flow_available": 130_000,
            "debt_service": 100_000,
            "cash": 50_000,
            "financial_debt": 250_000,
            "equity": 350_000,
            "total_assets": 900_000,
            "current_assets": 400_000,
            "current_liabilities": 300_000,
        }
    )
    financials = db.list_financials(client_id)
    assert len(financials) == 1
    assert financials[0]["revenue"] == 1_000_000


def test_pdf_report_generation(tmp_path: Path) -> None:
    _isolated_storage(tmp_path)
    client_id = db.save_client({"name": "Alfa S.r.l.", "vat": "12345678901"})
    client = db.get_client(client_id)
    financial = {
        "fiscal_year": 2025,
        "revenue": 2_000_000,
        "ebitda": 300_000,
        "financial_debt": 400_000,
        "cash": 100_000,
        "cash_flow_available": 220_000,
        "debt_service": 150_000,
        "equity": 500_000,
        "total_assets": 1_500_000,
        "current_assets": 700_000,
        "current_liabilities": 500_000,
    }
    rating = score_rating(financial_kpis(financial), {"granted": 500_000, "utilized": 300_000})
    pdf = build_bank_dossier(client, [financial], [], [], [], rating, ["Visura"])
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 2_000


def test_mandates_offers_automations_and_backup(tmp_path: Path) -> None:
    _isolated_storage(tmp_path)
    client_id = db.save_client({"name": "Beta S.r.l."})
    practice_id = db.save_practice(
        {"client_id": client_id, "practice_type": "Chirografario", "amount_requested": 300_000}
    )
    db.save_mandate(
        {
            "client_id": client_id, "practice_id": practice_id, "subject": "Finanza impresa",
            "base_amount": 300_000, "percentage": 2.0, "minimum_fee": 2_000, "deposits": 1_000,
        }
    )
    mandate = db.list_mandates(client_id)[0]
    assert mandate["calculated_fee"] == 6_000
    db.save_bank_offer(
        {
            "client_id": client_id, "practice_id": practice_id, "institution": "Banca Test",
            "product": "Chirografario", "amount": 300_000, "tan": 5.5, "taeg": 6.2,
            "duration_months": 60,
        }
    )
    assert db.list_bank_offers(client_id)[0]["institution"] == "Banca Test"
    db.save_automation({"name": "Controllo allegati", "source": "Gmail", "cadence": "Giornaliera"})
    assert db.list_automations()[0]["name"] == "Controllo allegati"
    backup = db.backup_bytes()
    assert backup.startswith(b"PK")
    assert len(db.list_audit_log()) >= 4
