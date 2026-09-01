"""Persistenza locale per FINANCE_PLUS_GOLD_GENERALE.

Il modulo usa solo SQLite e la libreria standard, così l'applicazione resta
avviabile in locale e su Streamlit Cloud senza servizi esterni obbligatori.
La directory dati è configurabile con ``FINANCEPLUS_DATA_DIR``.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import sqlite3
import uuid
import zipfile
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("FINANCEPLUS_DATA_DIR", str(APP_DIR / "data"))).expanduser()
DOCUMENTS_DIR = DATA_DIR / "documenti"
DB_PATH = DATA_DIR / "financeplus_gold_generale.sqlite3"


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    vat TEXT DEFAULT '',
    tax_code TEXT DEFAULT '',
    rea TEXT DEFAULT '',
    legal_form TEXT DEFAULT '',
    ateco TEXT DEFAULT '',
    pec TEXT DEFAULT '',
    email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    legal_address TEXT DEFAULT '',
    administrator TEXT DEFAULT '',
    manager TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Attivo',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_clients_vat ON clients(vat);
CREATE INDEX IF NOT EXISTS idx_clients_tax_code ON clients(tax_code);

CREATE TABLE IF NOT EXISTS practices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    practice_type TEXT NOT NULL,
    institution TEXT DEFAULT '',
    amount_requested REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Da avviare',
    priority TEXT NOT NULL DEFAULT 'Media',
    opened_on TEXT DEFAULT '',
    due_on TEXT DEFAULT '',
    next_action TEXT DEFAULT '',
    completeness REAL NOT NULL DEFAULT 0,
    probability REAL NOT NULL DEFAULT 0,
    max_amount REAL NOT NULL DEFAULT 0,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_practices_client ON practices(client_id);
CREATE INDEX IF NOT EXISTS idx_practices_due ON practices(due_on);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Altro',
    document_date TEXT DEFAULT '',
    fiscal_year INTEGER,
    source TEXT DEFAULT 'Caricamento manuale',
    verification_status TEXT NOT NULL DEFAULT 'Da verificare',
    notes TEXT DEFAULT '',
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(client_id, sha256)
);

CREATE INDEX IF NOT EXISTS idx_documents_client ON documents(client_id);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);

CREATE TABLE IF NOT EXISTS financials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    fiscal_year INTEGER NOT NULL,
    revenue REAL NOT NULL DEFAULT 0,
    ebitda REAL NOT NULL DEFAULT 0,
    ebit REAL NOT NULL DEFAULT 0,
    net_income REAL NOT NULL DEFAULT 0,
    cash_flow_available REAL NOT NULL DEFAULT 0,
    debt_service REAL NOT NULL DEFAULT 0,
    cash REAL NOT NULL DEFAULT 0,
    financial_debt REAL NOT NULL DEFAULT 0,
    equity REAL NOT NULL DEFAULT 0,
    current_assets REAL NOT NULL DEFAULT 0,
    current_liabilities REAL NOT NULL DEFAULT 0,
    total_assets REAL NOT NULL DEFAULT 0,
    total_debt REAL NOT NULL DEFAULT 0,
    receivables REAL NOT NULL DEFAULT 0,
    payables REAL NOT NULL DEFAULT 0,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(client_id, fiscal_year)
);

CREATE INDEX IF NOT EXISTS idx_financials_client_year ON financials(client_id, fiscal_year);

CREATE TABLE IF NOT EXISTS credit_risk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    reference_date TEXT NOT NULL,
    granted REAL NOT NULL DEFAULT 0,
    utilized REAL NOT NULL DEFAULT 0,
    overdue REAL NOT NULL DEFAULT 0,
    past_due REAL NOT NULL DEFAULT 0,
    guarantees REAL NOT NULL DEFAULT 0,
    number_banks INTEGER NOT NULL DEFAULT 0,
    anomalies TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(client_id, reference_date)
);

CREATE INDEX IF NOT EXISTS idx_credit_risk_client_date ON credit_risk(client_id, reference_date);

CREATE TABLE IF NOT EXISTS deadlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    due_on TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'Media',
    status TEXT NOT NULL DEFAULT 'Da fare',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_deadlines_due ON deadlines(due_on);

CREATE TABLE IF NOT EXISTS mandates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    practice_id INTEGER REFERENCES practices(id) ON DELETE SET NULL,
    subject TEXT NOT NULL,
    signed_on TEXT DEFAULT '',
    fee_basis TEXT NOT NULL DEFAULT 'Importo erogato',
    base_amount REAL NOT NULL DEFAULT 0,
    percentage REAL NOT NULL DEFAULT 0,
    minimum_fee REAL NOT NULL DEFAULT 0,
    calculated_fee REAL NOT NULL DEFAULT 0,
    deposits REAL NOT NULL DEFAULT 0,
    due_on TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Attivo',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mandates_client ON mandates(client_id);

CREATE TABLE IF NOT EXISTS bank_offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    practice_id INTEGER REFERENCES practices(id) ON DELETE SET NULL,
    institution TEXT NOT NULL,
    product TEXT NOT NULL,
    amount REAL NOT NULL DEFAULT 0,
    tan REAL NOT NULL DEFAULT 0,
    taeg REAL NOT NULL DEFAULT 0,
    duration_months INTEGER NOT NULL DEFAULT 0,
    prepayment_months INTEGER NOT NULL DEFAULT 0,
    guarantees TEXT DEFAULT '',
    fees REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Da valutare',
    offer_date TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bank_offers_client ON bank_offers(client_id);

CREATE TABLE IF NOT EXISTS automation_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source TEXT NOT NULL,
    cadence TEXT NOT NULL DEFAULT 'Giornaliera',
    filter_rule TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Da configurare',
    last_run TEXT DEFAULT '',
    last_result TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT DEFAULT '',
    detail TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(event_time);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _iso(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return str(value)[:10]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        text = str(value).strip().replace(" ", "")
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")
        return float(text)


def _integer(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    ensure_storage()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connection() as conn:
        conn.executescript(SCHEMA)


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(row) for row in rows]


def log_event(action: str, entity_type: str, entity_id: Any = "", detail: str = "") -> None:
    with connection() as conn:
        conn.execute(
            "INSERT INTO audit_log (event_time,action,entity_type,entity_id,detail) VALUES (?,?,?,?,?)",
            (_now(), _clean_text(action), _clean_text(entity_type), _clean_text(entity_id), _clean_text(detail)),
        )


def list_audit_log(limit: int = 200) -> List[Dict[str, Any]]:
    with connection() as conn:
        return rows_to_dicts(
            conn.execute("SELECT * FROM audit_log ORDER BY event_time DESC LIMIT ?", (max(1, int(limit)),)).fetchall()
        )


def dashboard_metrics() -> Dict[str, Any]:
    today = date.today().isoformat()
    with connection() as conn:
        clients = conn.execute("SELECT COUNT(*) FROM clients WHERE status != 'Archiviato'").fetchone()[0]
        active_practices = conn.execute(
            "SELECT COUNT(*) FROM practices WHERE status NOT IN ('Erogata','Chiusa','Respinta')"
        ).fetchone()[0]
        requested = conn.execute(
            "SELECT COALESCE(SUM(amount_requested),0) FROM practices "
            "WHERE status NOT IN ('Erogata','Chiusa','Respinta')"
        ).fetchone()[0]
        documents = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        due = conn.execute(
            "SELECT COUNT(*) FROM deadlines WHERE due_on <= ? AND status != 'Completata'", (today,)
        ).fetchone()[0]
    return {
        "clients": clients,
        "active_practices": active_practices,
        "requested_amount": requested,
        "documents": documents,
        "due_deadlines": due,
    }


def list_clients(query: str = "") -> List[Dict[str, Any]]:
    needle = f"%{query.strip()}%"
    sql = """
        SELECT c.*,
               (SELECT COUNT(*) FROM practices p WHERE p.client_id=c.id) AS practice_count,
               (SELECT COUNT(*) FROM documents d WHERE d.client_id=c.id) AS document_count
        FROM clients c
        WHERE ? = '%%'
           OR c.name LIKE ? COLLATE NOCASE
           OR c.vat LIKE ?
           OR c.tax_code LIKE ?
           OR c.pec LIKE ? COLLATE NOCASE
           OR c.email LIKE ? COLLATE NOCASE
        ORDER BY c.name COLLATE NOCASE
    """
    with connection() as conn:
        return rows_to_dicts(conn.execute(sql, (needle, needle, needle, needle, needle, needle)).fetchall())


def get_client(client_id: int) -> Optional[Dict[str, Any]]:
    with connection() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id=?", (int(client_id),)).fetchone()
    return dict(row) if row else None


def save_client(values: Mapping[str, Any], client_id: Optional[int] = None) -> int:
    name = _clean_text(values.get("name"))
    if not name:
        raise ValueError("La denominazione del cliente è obbligatoria.")
    fields = [
        "name", "vat", "tax_code", "rea", "legal_form", "ateco", "pec", "email", "phone",
        "legal_address", "administrator", "manager", "status", "notes",
    ]
    payload = {key: _clean_text(values.get(key)) for key in fields}
    payload["status"] = payload["status"] or "Attivo"
    now = _now()
    with connection() as conn:
        if client_id:
            assignments = ", ".join(f"{field}=?" for field in fields)
            conn.execute(
                f"UPDATE clients SET {assignments}, updated_at=? WHERE id=?",
                [payload[field] for field in fields] + [now, int(client_id)],
            )
            return int(client_id)
        placeholders = ",".join("?" for _ in fields)
        cursor = conn.execute(
            f"INSERT INTO clients ({','.join(fields)},created_at,updated_at) "
            f"VALUES ({placeholders},?,?)",
            [payload[field] for field in fields] + [now, now],
        )
        result = int(cursor.lastrowid)
    log_event("CREATE", "client", result, name)
    return result


def list_practices(client_id: Optional[int] = None) -> List[Dict[str, Any]]:
    sql = """
        SELECT p.*, c.name AS client_name
        FROM practices p JOIN clients c ON c.id=p.client_id
    """
    params: Sequence[Any] = ()
    if client_id:
        sql += " WHERE p.client_id=?"
        params = (int(client_id),)
    sql += " ORDER BY CASE WHEN p.due_on='' THEN 1 ELSE 0 END, p.due_on, p.updated_at DESC"
    with connection() as conn:
        return rows_to_dicts(conn.execute(sql, params).fetchall())


def save_practice(values: Mapping[str, Any], practice_id: Optional[int] = None) -> int:
    client_id = _integer(values.get("client_id"))
    practice_type = _clean_text(values.get("practice_type"))
    if not client_id or not practice_type:
        raise ValueError("Cliente e tipo pratica sono obbligatori.")
    fields = [
        "client_id", "practice_type", "institution", "amount_requested", "status", "priority",
        "opened_on", "due_on", "next_action", "completeness", "probability", "max_amount", "notes",
    ]
    payload: Dict[str, Any] = {
        "client_id": client_id,
        "practice_type": practice_type,
        "institution": _clean_text(values.get("institution")),
        "amount_requested": _number(values.get("amount_requested")),
        "status": _clean_text(values.get("status")) or "Da avviare",
        "priority": _clean_text(values.get("priority")) or "Media",
        "opened_on": _iso(values.get("opened_on")),
        "due_on": _iso(values.get("due_on")),
        "next_action": _clean_text(values.get("next_action")),
        "completeness": min(max(_number(values.get("completeness")), 0), 100),
        "probability": min(max(_number(values.get("probability")), 0), 100),
        "max_amount": _number(values.get("max_amount")),
        "notes": _clean_text(values.get("notes")),
    }
    now = _now()
    with connection() as conn:
        if practice_id:
            assignments = ", ".join(f"{field}=?" for field in fields)
            conn.execute(
                f"UPDATE practices SET {assignments}, updated_at=? WHERE id=?",
                [payload[field] for field in fields] + [now, int(practice_id)],
            )
            return int(practice_id)
        placeholders = ",".join("?" for _ in fields)
        cur = conn.execute(
            f"INSERT INTO practices ({','.join(fields)},created_at,updated_at) "
            f"VALUES ({placeholders},?,?)",
            [payload[field] for field in fields] + [now, now],
        )
        result = int(cur.lastrowid)
    log_event("CREATE", "practice", result, practice_type)
    return result


def _safe_name(filename: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", Path(filename).name).strip(" ._")
    return stem[:180] or "documento"


def save_document(
    client_id: int,
    filename: str,
    content: bytes,
    category: str,
    document_date: Any = "",
    fiscal_year: Optional[int] = None,
    source: str = "Caricamento manuale",
    verification_status: str = "Da verificare",
    notes: str = "",
) -> tuple[int, bool]:
    if not content:
        raise ValueError("Il documento è vuoto.")
    digest = hashlib.sha256(content).hexdigest()
    with connection() as conn:
        duplicate = conn.execute(
            "SELECT id FROM documents WHERE client_id=? AND sha256=?", (int(client_id), digest)
        ).fetchone()
        if duplicate:
            return int(duplicate[0]), False

    client = get_client(client_id)
    if not client:
        raise ValueError("Cliente non trovato.")
    year = int(fiscal_year) if fiscal_year else (date.today().year)
    category_folder = re.sub(r"[^A-Za-z0-9_-]+", "_", category).strip("_") or "Altro"
    client_folder = f"{int(client_id):05d}_{_safe_name(client['name'])}"
    folder = DOCUMENTS_DIR / client_folder / str(year) / category_folder
    folder.mkdir(parents=True, exist_ok=True)
    stored = folder / f"{uuid.uuid4().hex[:10]}_{_safe_name(filename)}"
    stored.write_bytes(content)

    try:
        with connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO documents (
                    client_id,original_name,stored_path,category,document_date,fiscal_year,source,
                    verification_status,notes,sha256,size_bytes,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    int(client_id), filename, str(stored.relative_to(DATA_DIR)), category,
                    _iso(document_date), year, source, verification_status, notes,
                    digest, len(content), _now(),
                ),
            )
            result = int(cur.lastrowid)
        log_event("CREATE", "document", result, filename)
        return result, True
    except Exception:
        stored.unlink(missing_ok=True)
        raise


def list_documents(client_id: Optional[int] = None, category: str = "", query: str = "") -> List[Dict[str, Any]]:
    clauses: List[str] = []
    params: List[Any] = []
    if client_id:
        clauses.append("d.client_id=?")
        params.append(int(client_id))
    if category and category != "Tutti":
        clauses.append("d.category=?")
        params.append(category)
    if query.strip():
        clauses.append("(d.original_name LIKE ? COLLATE NOCASE OR c.name LIKE ? COLLATE NOCASE)")
        params.extend([f"%{query.strip()}%", f"%{query.strip()}%"])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    sql = (
        "SELECT d.*, c.name AS client_name FROM documents d "
        "JOIN clients c ON c.id=d.client_id" + where + " ORDER BY d.created_at DESC"
    )
    with connection() as conn:
        return rows_to_dicts(conn.execute(sql, params).fetchall())


def read_document(document_id: int) -> tuple[Dict[str, Any], bytes]:
    with connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (int(document_id),)).fetchone()
    if not row:
        raise FileNotFoundError("Documento non trovato nel database.")
    record = dict(row)
    path = (DATA_DIR / record["stored_path"]).resolve()
    root = DATA_DIR.resolve()
    if root not in path.parents:
        raise ValueError("Percorso documento non valido.")
    return record, path.read_bytes()


def save_financial(values: Mapping[str, Any]) -> int:
    client_id = _integer(values.get("client_id"))
    fiscal_year = _integer(values.get("fiscal_year"))
    if not client_id or not fiscal_year:
        raise ValueError("Cliente ed esercizio sono obbligatori.")
    numeric_fields = [
        "revenue", "ebitda", "ebit", "net_income", "cash_flow_available", "debt_service", "cash",
        "financial_debt", "equity", "current_assets", "current_liabilities", "total_assets", "total_debt",
        "receivables", "payables",
    ]
    payload = {field: _number(values.get(field)) for field in numeric_fields}
    notes = _clean_text(values.get("notes"))
    now = _now()
    with connection() as conn:
        conn.execute(
            f"""
            INSERT INTO financials (client_id,fiscal_year,{','.join(numeric_fields)},notes,created_at,updated_at)
            VALUES ({','.join('?' for _ in range(2 + len(numeric_fields) + 3))})
            ON CONFLICT(client_id,fiscal_year) DO UPDATE SET
            {','.join(f'{field}=excluded.{field}' for field in numeric_fields)},
            notes=excluded.notes, updated_at=excluded.updated_at
            """,
            [client_id, fiscal_year] + [payload[field] for field in numeric_fields] + [notes, now, now],
        )
        row = conn.execute(
            "SELECT id FROM financials WHERE client_id=? AND fiscal_year=?", (client_id, fiscal_year)
        ).fetchone()
        return int(row[0])


def list_financials(client_id: int) -> List[Dict[str, Any]]:
    with connection() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM financials WHERE client_id=? ORDER BY fiscal_year", (int(client_id),)
            ).fetchall()
        )


def save_credit_risk(values: Mapping[str, Any]) -> int:
    client_id = _integer(values.get("client_id"))
    reference_date = _iso(values.get("reference_date"))
    if not client_id or not reference_date:
        raise ValueError("Cliente e data di riferimento sono obbligatori.")
    numeric_fields = ["granted", "utilized", "overdue", "past_due", "guarantees"]
    payload = {field: _number(values.get(field)) for field in numeric_fields}
    number_banks = _integer(values.get("number_banks"))
    anomalies = _clean_text(values.get("anomalies"))
    now = _now()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO credit_risk (
                client_id,reference_date,granted,utilized,overdue,past_due,guarantees,
                number_banks,anomalies,created_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(client_id,reference_date) DO UPDATE SET
                granted=excluded.granted, utilized=excluded.utilized, overdue=excluded.overdue,
                past_due=excluded.past_due, guarantees=excluded.guarantees,
                number_banks=excluded.number_banks, anomalies=excluded.anomalies,
                updated_at=excluded.updated_at
            """,
            (
                client_id, reference_date, payload["granted"], payload["utilized"], payload["overdue"],
                payload["past_due"], payload["guarantees"], number_banks, anomalies, now, now,
            ),
        )
        row = conn.execute(
            "SELECT id FROM credit_risk WHERE client_id=? AND reference_date=?",
            (client_id, reference_date),
        ).fetchone()
        return int(row[0])


def list_credit_risk(client_id: int) -> List[Dict[str, Any]]:
    with connection() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM credit_risk WHERE client_id=? ORDER BY reference_date", (int(client_id),)
            ).fetchall()
        )


def save_deadline(values: Mapping[str, Any]) -> int:
    title = _clean_text(values.get("title"))
    due_on = _iso(values.get("due_on"))
    if not title or not due_on:
        raise ValueError("Titolo e scadenza sono obbligatori.")
    now = _now()
    with connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO deadlines (client_id,title,due_on,priority,status,notes,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                _integer(values.get("client_id")) or None, title, due_on,
                _clean_text(values.get("priority")) or "Media",
                _clean_text(values.get("status")) or "Da fare",
                _clean_text(values.get("notes")), now, now,
            ),
        )
        return int(cur.lastrowid)


def list_deadlines(mode: str = "Tutte") -> List[Dict[str, Any]]:
    today = date.today().isoformat()
    clauses: List[str] = []
    params: List[Any] = []
    if mode == "Scadute":
        clauses.append("d.due_on < ? AND d.status != 'Completata'")
        params.append(today)
    elif mode == "Oggi":
        clauses.append("d.due_on = ?")
        params.append(today)
    elif mode == "Aperte":
        clauses.append("d.status != 'Completata'")
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    sql = (
        "SELECT d.*, COALESCE(c.name,'—') AS client_name FROM deadlines d "
        "LEFT JOIN clients c ON c.id=d.client_id" + where + " ORDER BY d.due_on, d.priority"
    )
    with connection() as conn:
        return rows_to_dicts(conn.execute(sql, params).fetchall())


def update_deadline_status(deadline_id: int, status: str) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE deadlines SET status=?, updated_at=? WHERE id=?",
            (_clean_text(status), _now(), int(deadline_id)),
        )


def missing_document_categories(client_id: int) -> List[str]:
    required = ["Visura", "Bilancio", "Centrale Rischi", "Estratto conto", "Documento identità"]
    with connection() as conn:
        present = {
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT category FROM documents WHERE client_id=?", (int(client_id),)
            ).fetchall()
        }
    return [category for category in required if category not in present]


def save_mandate(values: Mapping[str, Any]) -> int:
    client_id = _integer(values.get("client_id"))
    subject = _clean_text(values.get("subject"))
    if not client_id or not subject:
        raise ValueError("Cliente e oggetto del mandato sono obbligatori.")
    base_amount = _number(values.get("base_amount"))
    percentage = _number(values.get("percentage"))
    minimum_fee = _number(values.get("minimum_fee"))
    calculated_fee = max(base_amount * percentage / 100, minimum_fee)
    now = _now()
    with connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO mandates (
                client_id,practice_id,subject,signed_on,fee_basis,base_amount,percentage,minimum_fee,
                calculated_fee,deposits,due_on,status,notes,created_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                client_id, _integer(values.get("practice_id")) or None, subject, _iso(values.get("signed_on")),
                _clean_text(values.get("fee_basis")) or "Importo erogato", base_amount, percentage, minimum_fee,
                calculated_fee, _number(values.get("deposits")), _iso(values.get("due_on")),
                _clean_text(values.get("status")) or "Attivo", _clean_text(values.get("notes")), now, now,
            ),
        )
        result = int(cur.lastrowid)
    log_event("CREATE", "mandate", result, subject)
    return result


def list_mandates(client_id: Optional[int] = None) -> List[Dict[str, Any]]:
    sql = """
        SELECT m.*, c.name AS client_name, p.practice_type
        FROM mandates m JOIN clients c ON c.id=m.client_id
        LEFT JOIN practices p ON p.id=m.practice_id
    """
    params: Sequence[Any] = ()
    if client_id:
        sql += " WHERE m.client_id=?"
        params = (int(client_id),)
    sql += " ORDER BY m.created_at DESC"
    with connection() as conn:
        return rows_to_dicts(conn.execute(sql, params).fetchall())


def save_bank_offer(values: Mapping[str, Any]) -> int:
    client_id = _integer(values.get("client_id"))
    institution = _clean_text(values.get("institution"))
    product = _clean_text(values.get("product"))
    if not client_id or not institution or not product:
        raise ValueError("Cliente, istituto e prodotto sono obbligatori.")
    now = _now()
    with connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO bank_offers (
                client_id,practice_id,institution,product,amount,tan,taeg,duration_months,
                prepayment_months,guarantees,fees,status,offer_date,notes,created_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                client_id, _integer(values.get("practice_id")) or None, institution, product,
                _number(values.get("amount")), _number(values.get("tan")), _number(values.get("taeg")),
                _integer(values.get("duration_months")), _integer(values.get("prepayment_months")),
                _clean_text(values.get("guarantees")), _number(values.get("fees")),
                _clean_text(values.get("status")) or "Da valutare", _iso(values.get("offer_date")),
                _clean_text(values.get("notes")), now, now,
            ),
        )
        result = int(cur.lastrowid)
    log_event("CREATE", "bank_offer", result, f"{institution} - {product}")
    return result


def list_bank_offers(client_id: Optional[int] = None) -> List[Dict[str, Any]]:
    sql = """
        SELECT o.*, c.name AS client_name, p.practice_type
        FROM bank_offers o JOIN clients c ON c.id=o.client_id
        LEFT JOIN practices p ON p.id=o.practice_id
    """
    params: Sequence[Any] = ()
    if client_id:
        sql += " WHERE o.client_id=?"
        params = (int(client_id),)
    sql += " ORDER BY o.offer_date DESC, o.created_at DESC"
    with connection() as conn:
        return rows_to_dicts(conn.execute(sql, params).fetchall())


def save_automation(values: Mapping[str, Any]) -> int:
    name = _clean_text(values.get("name"))
    source = _clean_text(values.get("source"))
    if not name or not source:
        raise ValueError("Nome e fonte dell'automazione sono obbligatori.")
    now = _now()
    with connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO automation_jobs (
                name,source,cadence,filter_rule,status,last_run,last_result,notes,created_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                name, source, _clean_text(values.get("cadence")) or "Giornaliera",
                _clean_text(values.get("filter_rule")), _clean_text(values.get("status")) or "Da configurare",
                _iso(values.get("last_run")), _clean_text(values.get("last_result")),
                _clean_text(values.get("notes")), now, now,
            ),
        )
        result = int(cur.lastrowid)
    log_event("CREATE", "automation", result, name)
    return result


def list_automations() -> List[Dict[str, Any]]:
    with connection() as conn:
        return rows_to_dicts(conn.execute("SELECT * FROM automation_jobs ORDER BY name COLLATE NOCASE").fetchall())


def backup_bytes() -> bytes:
    """Crea un backup ZIP in memoria di database e archivio documentale."""
    ensure_storage()
    with connection() as conn:
        conn.execute("PRAGMA wal_checkpoint(FULL)")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if DB_PATH.exists():
            archive.write(DB_PATH, arcname="financeplus_gold_generale.sqlite3")
        if DOCUMENTS_DIR.exists():
            for path in DOCUMENTS_DIR.rglob("*"):
                if path.is_file():
                    archive.write(path, arcname=str(Path("documenti") / path.relative_to(DOCUMENTS_DIR)))
    return buffer.getvalue()


init_db()
