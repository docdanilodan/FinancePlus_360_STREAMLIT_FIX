"""
FinancePlus 360 - Streamlit Cloud SAFE
======================================

Questa e' la versione web per GitHub/Streamlit Cloud.
NON importa tkinter e quindi risolve l'errore:
"ImportError: libtk... Python may not be configured for Tk".

La versione desktop originale Tkinter si trova in:
    desktop/FinancePlus_360_DESKTOP_TKINTER.py

Avvio locale:
    streamlit run FinancePlus_360.py
"""

from __future__ import annotations

import csv
import email
import hashlib
import imaplib
import io
import json
import os
import re
import ssl
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from email.header import decode_header
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import streamlit as st

APP_NAME = "FinancePlus Mail Downloader 360"
APP_VERSION = "5.1-streamlit-cloud-safe"
LOCAL_CONFIG_FILE = Path("financeplus_mail_config.local.json")
LOCAL_OUTPUT_DIR = Path("mail_scaricate")

DEFAULT_SENDERS = [
    "elibetty731@gmail.com",
    "valentinaboratto82@gmail.com",
    "stefano.faraone@eurofintechsrl.it",
    "pratichebs@proton.me",
    "sergio.pedolazzi@katudi.it",
    "paolo.baldinelli@katudi.it",
    "pratiche@katudi.it",
    "niccolo.sovico@ener2crowd.com",
]

DEFAULT_ACCOUNTS = [
    {
        "active": True,
        "name": "Account 1 Gmail",
        "email_account": "dangelo.danilo.pri@gmail.com",
        "password": "",
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "mailbox": "INBOX",
        "ignore_ssl_errors": False,
    },
    {
        "active": False,
        "name": "FinancePlus pratiche",
        "email_account": "pratiche@financeplus.tech",
        "password": "",
        "imap_host": "imap.aruba.com",
        "imap_port": 993,
        "mailbox": "INBOX",
        "ignore_ssl_errors": False,
    },
    {
        "active": False,
        "name": "FinancePlus d.dangelo",
        "email_account": "d.dangelo@financeplus.tech",
        "password": "",
        "imap_host": "imap.aruba.com",
        "imap_port": 993,
        "mailbox": "INBOX",
        "ignore_ssl_errors": False,
    },
]

COMPANY_SUFFIX_RE = re.compile(
    r"([A-Z0-9&' .\-]{3,80}\s+(?:S\.?R\.?L\.?|S\.?P\.?A\.?|SRLS|SNC|SAS|SOC\.?\s*COOP\.?|COOPERATIVA|DITTA|IMPRESA))",
    re.IGNORECASE,
)
VAT_RE = re.compile(r"(?:P\.?\s*IVA|PARTITA\s+IVA|PIVA)\s*[:#\-]?\s*([0-9]{11})", re.IGNORECASE)
CF_RE = re.compile(r"(?:C\.?F\.?|CODICE\s+FISCALE)\s*[:#\-]?\s*([A-Z0-9]{11,16})", re.IGNORECASE)


@dataclass
class MailAccount:
    active: bool = False
    name: str = ""
    email_account: str = ""
    password: str = ""
    imap_host: str = ""
    imap_port: int = 993
    mailbox: str = "INBOX"
    ignore_ssl_errors: bool = False


@dataclass
class AppConfig:
    accounts: List[MailAccount] = field(default_factory=list)
    senders: List[str] = field(default_factory=list)
    save_eml: bool = True
    save_local_copy: bool = True
    mark_seen: bool = False
    delete_after_download: bool = False


def normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def clean_filename(value: str, fallback: str = "senza_nome") -> str:
    value = decode_mime_words(value or "")
    value = re.sub(r"[\\/:*?\"<>|\r\n\t]+", "_", value).strip(" ._")
    value = re.sub(r"\s+", " ", value)
    return value[:160] or fallback


def clean_folder(value: str, fallback: str = "_TEMP_DA_ABBINARE") -> str:
    value = decode_mime_words(value or "")
    value = re.sub(r"[\\/:*?\"<>|\r\n\t]+", "_", value).strip(" ._")
    value = re.sub(r"\s+", " ", value)
    return value[:80] or fallback


def decode_mime_words(value: str) -> str:
    if not value:
        return ""
    parts: List[str] = []
    for raw, charset in decode_header(value):
        if isinstance(raw, bytes):
            for enc in [charset, "utf-8", "latin-1", "cp1252"]:
                if not enc:
                    continue
                try:
                    parts.append(raw.decode(enc, errors="replace"))
                    break
                except Exception:
                    continue
            else:
                parts.append(raw.decode("utf-8", errors="replace"))
        else:
            parts.append(str(raw))
    return "".join(parts)


def message_text(msg: Message, max_chars: int = 8000) -> str:
    chunks: List[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            dispo = str(part.get("Content-Disposition", "")).lower()
            if ctype in ("text/plain", "text/html") and "attachment" not in dispo:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        text = payload.decode(charset, errors="replace")
                    except Exception:
                        text = payload.decode("utf-8", errors="replace")
                    if ctype == "text/html":
                        text = re.sub(r"<[^>]+>", " ", text)
                    chunks.append(text)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            chunks.append(payload.decode(charset, errors="replace"))
    return re.sub(r"\s+", " ", " ".join(chunks))[:max_chars]


def extract_sender(msg: Message) -> Tuple[str, str]:
    raw_from = decode_mime_words(msg.get("From", ""))
    parsed = getaddresses([raw_from])
    if parsed:
        name, addr = parsed[0]
        return clean_folder(name or addr), normalize_email(addr)
    return "mittente_sconosciuto", ""


def extract_date(msg: Message) -> datetime:
    raw = msg.get("Date")
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo:
                return dt.astimezone().replace(tzinfo=None)
            return dt
        except Exception:
            pass
    return datetime.now()


def detect_client_name(subject: str, body: str, filenames: List[str], sender_name: str, sender_email: str) -> Tuple[str, str]:
    blob = " ".join([subject, body[:2000], " ".join(filenames)]).upper()
    match = COMPANY_SUFFIX_RE.search(blob)
    if match:
        return clean_folder(match.group(1).title()), "ragione sociale rilevata da oggetto/testo/allegati"

    vat = VAT_RE.search(blob)
    if vat:
        return f"PIVA_{vat.group(1)}", "partita IVA rilevata"

    cf = CF_RE.search(blob)
    if cf:
        return f"CF_{cf.group(1)}", "codice fiscale rilevato"

    if sender_email:
        local = sender_email.split("@")[0]
        if len(local) >= 4 and not re.fullmatch(r"info|admin|amministrazione|contabilita|pratiche", local, re.I):
            return clean_folder(local.title()), "derivato dal mittente"

    if sender_name and sender_name != "mittente_sconosciuto":
        return clean_folder(sender_name.title()), "derivato dal nome mittente"

    return "_TEMP_DA_ABBINARE", "non abbinato automaticamente"


def build_imap_date(d: date) -> str:
    return d.strftime("%d-%b-%Y")


def load_default_config() -> AppConfig:
    return AppConfig(
        accounts=[MailAccount(**a) for a in DEFAULT_ACCOUNTS],
        senders=DEFAULT_SENDERS[:],
        save_eml=True,
        save_local_copy=True,
        mark_seen=False,
        delete_after_download=False,
    )


def load_config_from_file(path: Path = LOCAL_CONFIG_FILE) -> Optional[AppConfig]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return config_from_dict(data)
    except Exception:
        return None


def load_config_from_secrets() -> Optional[AppConfig]:
    """Optional Streamlit Cloud config via secrets.toml.

    Expected format:
    [financeplus_mail]
    senders = "a@x.it\nb@y.it"

    [[financeplus_mail.accounts]] is not supported by every secrets parser;
    therefore we accept JSON string accounts_json.
    """
    try:
        section = st.secrets.get("financeplus_mail", None)  # type: ignore[attr-defined]
    except Exception:
        return None
    if not section:
        return None
    cfg = load_default_config()
    try:
        if section.get("senders"):
            cfg.senders = parse_lines(str(section.get("senders")))
        if section.get("accounts_json"):
            accounts_raw = json.loads(str(section.get("accounts_json")))
            cfg.accounts = [MailAccount(**item) for item in accounts_raw]
        return cfg
    except Exception:
        return None


def config_from_dict(data: Dict[str, Any]) -> AppConfig:
    accounts = [MailAccount(**item) for item in data.get("accounts", [])]
    return AppConfig(
        accounts=accounts or [MailAccount(**a) for a in DEFAULT_ACCOUNTS],
        senders=parse_lines("\n".join(data.get("senders", DEFAULT_SENDERS))),
        save_eml=bool(data.get("save_eml", True)),
        save_local_copy=bool(data.get("save_local_copy", True)),
        mark_seen=bool(data.get("mark_seen", False)),
        delete_after_download=bool(data.get("delete_after_download", False)),
    )


def config_to_json(cfg: AppConfig, include_passwords: bool = True) -> str:
    data = asdict(cfg)
    if not include_passwords:
        for acc in data.get("accounts", []):
            acc["password"] = ""
    return json.dumps(data, indent=2, ensure_ascii=False)


def parse_lines(text: str) -> List[str]:
    values: List[str] = []
    seen = set()
    for line in (text or "").replace(";", "\n").replace(",", "\n").splitlines():
        item = normalize_email(line)
        if item and item not in seen:
            values.append(item)
            seen.add(item)
    return values


def imap_connect(account: MailAccount) -> imaplib.IMAP4_SSL:
    if account.ignore_ssl_errors:
        context = ssl._create_unverified_context()
    else:
        context = ssl.create_default_context()
    return imaplib.IMAP4_SSL(account.imap_host, int(account.imap_port), ssl_context=context)


def test_account(account: MailAccount) -> Tuple[bool, str]:
    if not account.email_account or not account.password or not account.imap_host:
        return False, "Dati mancanti: email, password app/IMAP o host IMAP."
    conn: Optional[imaplib.IMAP4_SSL] = None
    try:
        conn = imap_connect(account)
        conn.login(account.email_account, account.password)
        status, _ = conn.select(account.mailbox or "INBOX", readonly=True)
        if status != "OK":
            return False, f"Login OK, ma cartella non aperta: {account.mailbox}"
        return True, "Connessione OK."
    except Exception as exc:
        return False, f"Errore connessione: {exc}"
    finally:
        try:
            if conn:
                conn.logout()
        except Exception:
            pass


def search_message_ids(conn: imaplib.IMAP4_SSL, sender: Optional[str], date_from: date, date_to: date) -> List[bytes]:
    criteria = ["SINCE", build_imap_date(date_from), "BEFORE", build_imap_date(date_to + timedelta(days=1))]
    if sender:
        criteria.extend(["FROM", f'"{sender}"'])
    status, data = conn.search(None, *criteria)
    if status != "OK" or not data:
        return []
    ids = data[0].split()
    return ids


def iter_attachments(msg: Message) -> Iterable[Tuple[str, bytes, str]]:
    for part in msg.walk():
        dispo = str(part.get("Content-Disposition", "")).lower()
        filename = part.get_filename()
        if filename:
            filename = decode_mime_words(filename)
        is_attachment = "attachment" in dispo or bool(filename)
        if not is_attachment:
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        ctype = part.get_content_type() or "application/octet-stream"
        yield clean_filename(filename or "allegato.bin"), payload, ctype


def add_to_zip(zf: zipfile.ZipFile, path: str, content: bytes, seen_paths: set[str]) -> str:
    path = path.replace("\\", "/").strip("/")
    base, ext = os.path.splitext(path)
    candidate = path
    counter = 2
    while candidate in seen_paths:
        candidate = f"{base}_{counter}{ext}"
        counter += 1
    zf.writestr(candidate, content)
    seen_paths.add(candidate)
    return candidate


def save_local_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def process_download(
    cfg: AppConfig,
    date_from: date,
    date_to: date,
    progress_cb=None,
) -> Tuple[bytes, Dict[str, Any]]:
    summary: Dict[str, Any] = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "version": APP_VERSION,
        "accounts": [],
        "emails_read": 0,
        "attachments_saved": 0,
        "eml_saved": 0,
        "duplicates_skipped": 0,
        "errors": [],
        "clients": {},
    }
    zip_buffer = io.BytesIO()
    seen_hashes: set[str] = set()
    seen_zip_paths: set[str] = set()
    anagrafica_rows: List[Dict[str, str]] = []

    active_accounts = [a for a in cfg.accounts if a.active]
    allowed_senders = parse_lines("\n".join(cfg.senders))

    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for account_index, account in enumerate(active_accounts, start=1):
            acc_info = {
                "name": account.name,
                "email_account": account.email_account,
                "messages_found": 0,
                "attachments_saved": 0,
                "errors": [],
            }
            summary["accounts"].append(acc_info)
            if progress_cb:
                progress_cb(f"Connessione a {account.email_account}...")
            conn: Optional[imaplib.IMAP4_SSL] = None
            try:
                conn = imap_connect(account)
                conn.login(account.email_account, account.password)
                status, _ = conn.select(account.mailbox or "INBOX", readonly=False)
                if status != "OK":
                    raise RuntimeError(f"Cartella IMAP non aperta: {account.mailbox}")

                if allowed_senders:
                    all_ids: List[bytes] = []
                    for sender in allowed_senders:
                        ids = search_message_ids(conn, sender, date_from, date_to)
                        all_ids.extend(ids)
                    # dedup preserving order
                    message_ids = list(dict.fromkeys(all_ids))
                else:
                    message_ids = search_message_ids(conn, None, date_from, date_to)

                acc_info["messages_found"] = len(message_ids)
                if progress_cb:
                    progress_cb(f"{account.email_account}: {len(message_ids)} mail trovate.")

                for pos, message_id in enumerate(message_ids, start=1):
                    status, data = conn.fetch(message_id, "(RFC822)")
                    if status != "OK" or not data or not data[0]:
                        continue
                    raw_email = data[0][1]
                    if not isinstance(raw_email, bytes):
                        continue
                    msg = email.message_from_bytes(raw_email)
                    summary["emails_read"] += 1

                    sender_name, sender_email = extract_sender(msg)
                    subject = clean_filename(decode_mime_words(msg.get("Subject", "senza oggetto")), "senza_oggetto")
                    msg_dt = extract_date(msg)
                    body = message_text(msg)
                    attachments = list(iter_attachments(msg))
                    filenames = [name for name, _, _ in attachments]
                    client, client_reason = detect_client_name(subject, body, filenames, sender_name, sender_email)
                    year = f"{msg_dt.year:04d}"
                    month = f"{msg_dt.month:02d}"
                    account_folder = clean_folder(account.email_account or account.name or f"account_{account_index}")
                    sender_folder = clean_folder(sender_email or sender_name)
                    prefix = f"mail_scaricate/{account_folder}/{client}/{year}/{month}"

                    summary["clients"].setdefault(client, {"reason": client_reason, "attachments": 0, "emails": 0})
                    summary["clients"][client]["emails"] += 1

                    if cfg.save_eml:
                        eml_name = f"{msg_dt.strftime('%Y-%m-%d_%H%M%S')}_{sender_folder}_{subject}.eml"
                        eml_path = f"{prefix}/EMAIL_EML/{clean_filename(eml_name, 'email.eml')}"
                        h = hashlib.sha256(raw_email).hexdigest()
                        if h in seen_hashes:
                            summary["duplicates_skipped"] += 1
                        else:
                            seen_hashes.add(h)
                            final_path = add_to_zip(zf, eml_path, raw_email, seen_zip_paths)
                            summary["eml_saved"] += 1
                            if cfg.save_local_copy:
                                save_local_file(Path(final_path), raw_email)

                    for filename, payload, ctype in attachments:
                        digest = hashlib.sha256(payload).hexdigest()
                        if digest in seen_hashes:
                            summary["duplicates_skipped"] += 1
                            continue
                        seen_hashes.add(digest)
                        nice_name = f"{msg_dt.strftime('%Y-%m-%d')}_{sender_folder}_{filename}"
                        attach_path = f"{prefix}/ALLEGATI/{clean_filename(nice_name, filename)}"
                        final_path = add_to_zip(zf, attach_path, payload, seen_zip_paths)
                        if cfg.save_local_copy:
                            save_local_file(Path(final_path), payload)
                        summary["attachments_saved"] += 1
                        acc_info["attachments_saved"] += 1
                        summary["clients"][client]["attachments"] += 1

                    anagrafica_rows.append(
                        {
                            "cliente": client,
                            "motivo_abbinamento": client_reason,
                            "mittente_nome": sender_name,
                            "mittente_email": sender_email,
                            "account": account.email_account,
                            "data_email": msg_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            "oggetto": subject,
                            "n_allegati": str(len(attachments)),
                        }
                    )

                    if cfg.mark_seen:
                        conn.store(message_id, "+FLAGS", "\\Seen")
                    if cfg.delete_after_download:
                        conn.store(message_id, "+FLAGS", "\\Deleted")

                    if progress_cb and pos % 10 == 0:
                        progress_cb(f"{account.email_account}: elaborate {pos}/{len(message_ids)} mail...")

                if cfg.delete_after_download:
                    conn.expunge()

            except Exception as exc:
                err = f"{account.email_account}: {exc}"
                summary["errors"].append(err)
                acc_info["errors"].append(str(exc))
            finally:
                try:
                    if conn:
                        conn.logout()
                except Exception:
                    pass

        # riepiloghi sempre inclusi nello ZIP
        zf.writestr("RIEPILOGO_DOWNLOAD.json", json.dumps(summary, indent=2, ensure_ascii=False))
        csv_buffer = io.StringIO()
        fieldnames = [
            "cliente",
            "motivo_abbinamento",
            "mittente_nome",
            "mittente_email",
            "account",
            "data_email",
            "oggetto",
            "n_allegati",
        ]
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for row in anagrafica_rows:
            writer.writerow(row)
        zf.writestr("ANAGRAFICA_CLIENTI_DA_MAIL.csv", csv_buffer.getvalue().encode("utf-8-sig"))

    zip_buffer.seek(0)
    summary["finished_at"] = datetime.now().isoformat(timespec="seconds")
    return zip_buffer.getvalue(), summary


def init_state() -> None:
    if "cfg" not in st.session_state:
        cfg = load_config_from_secrets() or load_config_from_file() or load_default_config()
        st.session_state.cfg = cfg


def render_accounts_editor(cfg: AppConfig) -> None:
    st.subheader("1. Account email da scaricare")
    st.caption("Per Gmail serve la password per app. Per Aruba/FinancePlus usare host IMAP, porta 993 e password della casella/app.")

    edited_accounts: List[MailAccount] = []
    for idx, account in enumerate(cfg.accounts):
        with st.expander(f"{idx + 1}. {account.name or account.email_account or 'Nuovo account'}", expanded=idx == 0):
            c1, c2, c3 = st.columns([1, 2, 2])
            active = c1.checkbox("Attivo", value=account.active, key=f"acc_active_{idx}")
            name = c2.text_input("Nome", value=account.name, key=f"acc_name_{idx}")
            email_account = c3.text_input("Email account", value=account.email_account, key=f"acc_email_{idx}")

            c4, c5, c6, c7 = st.columns([2, 2, 1, 1])
            password = c4.text_input("Password app/IMAP", value=account.password, type="password", key=f"acc_pwd_{idx}")
            imap_host = c5.text_input("Host IMAP", value=account.imap_host, key=f"acc_host_{idx}")
            imap_port = c6.number_input("Porta", min_value=1, max_value=65535, value=int(account.imap_port or 993), step=1, key=f"acc_port_{idx}")
            mailbox = c7.text_input("Cartella", value=account.mailbox or "INBOX", key=f"acc_box_{idx}")
            ignore_ssl = st.checkbox("Ignora errori SSL solo se necessario", value=account.ignore_ssl_errors, key=f"acc_ssl_{idx}")

            edited_accounts.append(
                MailAccount(
                    active=active,
                    name=name,
                    email_account=email_account,
                    password=password,
                    imap_host=imap_host,
                    imap_port=int(imap_port),
                    mailbox=mailbox or "INBOX",
                    ignore_ssl_errors=ignore_ssl,
                )
            )
    cfg.accounts = edited_accounts

    cc1, cc2 = st.columns([1, 1])
    if cc1.button("+ Aggiungi account vuoto"):
        cfg.accounts.append(MailAccount(active=False, name="Nuovo account", imap_port=993, mailbox="INBOX"))
        st.rerun()
    if cc2.button("Ripristina 3 account default"):
        cfg.accounts = [MailAccount(**a) for a in DEFAULT_ACCOUNTS]
        st.rerun()


def render_config_panel(cfg: AppConfig) -> None:
    st.subheader("2. Mittenti da monitorare")
    senders_text = st.text_area(
        "Un mittente per riga",
        value="\n".join(cfg.senders),
        height=170,
        help="Lascia vuoto per scaricare tutte le email nel periodo selezionato.",
    )
    cfg.senders = parse_lines(senders_text)

    st.subheader("3. Opzioni salvataggio")
    c1, c2, c3, c4 = st.columns(4)
    cfg.save_eml = c1.checkbox("Salva anche .eml", value=cfg.save_eml)
    cfg.save_local_copy = c2.checkbox("Salva copia locale server", value=cfg.save_local_copy)
    cfg.mark_seen = c3.checkbox("Marca come lette", value=cfg.mark_seen)
    cfg.delete_after_download = c4.checkbox("Elimina dopo salvataggio", value=cfg.delete_after_download)
    if cfg.delete_after_download:
        st.warning("Eliminazione attiva: le mail elaborate saranno marcate come eliminate via IMAP. Usare solo dopo verifica del download.")


def render_save_load(cfg: AppConfig) -> None:
    st.subheader("4. Salva / carica configurazione")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Salva configurazione locale"):
            try:
                LOCAL_CONFIG_FILE.write_text(config_to_json(cfg, include_passwords=True), encoding="utf-8")
                st.success(f"Configurazione salvata in {LOCAL_CONFIG_FILE}")
            except Exception as exc:
                st.error(f"Salvataggio non riuscito: {exc}")
    with c2:
        st.download_button(
            "Scarica config JSON",
            data=config_to_json(cfg, include_passwords=True).encode("utf-8"),
            file_name="financeplus_mail_config.local.json",
            mime="application/json",
        )
    with c3:
        uploaded = st.file_uploader("Carica config JSON", type=["json"], label_visibility="collapsed")
        if uploaded is not None:
            try:
                loaded = config_from_dict(json.loads(uploaded.getvalue().decode("utf-8")))
                st.session_state.cfg = loaded
                st.success("Configurazione caricata.")
                st.rerun()
            except Exception as exc:
                st.error(f"Config non valida: {exc}")


def render_connection_tests(cfg: AppConfig) -> None:
    st.subheader("5. Test connessioni")
    if st.button("Testa account attivi"):
        for account in [a for a in cfg.accounts if a.active]:
            ok, msg = test_account(account)
            if ok:
                st.success(f"{account.email_account}: {msg}")
            else:
                st.error(f"{account.email_account}: {msg}")


def render_download(cfg: AppConfig) -> None:
    st.subheader("6. Scarica allegati/email")
    today = date.today()
    c1, c2 = st.columns(2)
    date_from = c1.date_input("Data inizio", value=today.replace(day=1))
    date_to = c2.date_input("Data fine", value=today)

    active_count = len([a for a in cfg.accounts if a.active])
    st.info(f"Account attivi: {active_count} | Mittenti monitorati: {len(cfg.senders)} | Versione: {APP_VERSION}")

    if st.button("Scarica allegati/email", type="primary", disabled=active_count == 0):
        status_box = st.empty()
        def progress(msg: str) -> None:
            status_box.info(msg)
        with st.spinner("Download in corso..."):
            zip_bytes, summary = process_download(cfg, date_from, date_to, progress_cb=progress)
        status_box.success("Download completato.")
        st.session_state.last_zip = zip_bytes
        st.session_state.last_summary = summary

    if "last_summary" in st.session_state:
        summary = st.session_state.last_summary
        st.success(
            f"Mail lette: {summary.get('emails_read', 0)} | Allegati salvati: {summary.get('attachments_saved', 0)} | "
            f"EML salvati: {summary.get('eml_saved', 0)} | Duplicati saltati: {summary.get('duplicates_skipped', 0)}"
        )
        if summary.get("errors"):
            st.error("Errori: " + " | ".join(summary.get("errors", [])))
        st.download_button(
            "Scarica ZIP archivio mail/allegati",
            data=st.session_state.last_zip,
            file_name=f"FinancePlus_mail_allegati_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
        )
        with st.expander("Riepilogo tecnico JSON"):
            st.json(summary)


def render_help() -> None:
    with st.sidebar:
        st.title("FinancePlus 360")
        st.caption("Versione web Streamlit senza Tkinter")
        st.markdown("---")
        st.markdown(
            "**Errore risolto:** su Streamlit Cloud non si puo' avviare una GUI desktop Tkinter. "
            "Questa app usa solo Streamlit."
        )
        st.markdown("---")
        st.markdown("**Per GitHub/Cloud**")
        st.code("streamlit run FinancePlus_360.py", language="bash")
        st.markdown("**File desktop originale**")
        st.code("desktop/FinancePlus_360_DESKTOP_TKINTER.py", language="text")


def require_access_password() -> bool:
    """Gate the app behind a password when ACCESS_PASSWORD is set in st.secrets.

    No-op (returns True immediately) when no secret is configured, so local
    Windows/desktop use stays password-free while a public Streamlit Cloud
    deployment can be locked down by setting ACCESS_PASSWORD in Settings > Secrets.
    """
    try:
        expected = st.secrets.get("ACCESS_PASSWORD", "")
    except Exception:
        expected = ""
    if not expected:
        return True
    if st.session_state.get("_access_ok"):
        return True
    st.title("🔒 FinancePlus 360 - Accesso protetto")
    pwd = st.text_input("Password di accesso", type="password")
    if st.button("Entra"):
        if pwd == expected:
            st.session_state["_access_ok"] = True
            st.rerun()
        else:
            st.error("Password errata.")
    return False


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="📩", layout="wide")
    if not require_access_password():
        return
    init_state()
    cfg: AppConfig = st.session_state.cfg

    render_help()
    st.title("📩 Scarica allegati/email - FinancePlus 360")
    st.caption("Multi account, mittenti filtrati, anti-duplicati, archivio ZIP, anagrafica clienti CSV, compatibile Streamlit Cloud.")

    tab1, tab2, tab3 = st.tabs(["Configurazione", "Download", "Guida rapida"])
    with tab1:
        render_accounts_editor(cfg)
        render_config_panel(cfg)
        render_save_load(cfg)
        render_connection_tests(cfg)
    with tab2:
        render_download(cfg)
    with tab3:
        st.markdown(
            """
### Perche' prima dava errore
Il file desktop importava `tkinter`. Streamlit Cloud gira su server Linux/headless e non espone una finestra grafica desktop; quindi l'import di Tk fallisce.

### Come usare su GitHub / Streamlit Cloud
1. Carica questa cartella su GitHub.
2. In Streamlit Cloud imposta come **Main file path**: `FinancePlus_360.py` oppure `streamlit_app.py`.
3. Inserisci le password app/IMAP dalla schermata Configurazione oppure tramite secrets.
4. Premi **Testa account attivi**.
5. Vai su Download e scarica lo ZIP finale.

### Nota sicurezza password
Non caricare mai file `financeplus_mail_config.local.json` su GitHub. E' gia' escluso nel `.gitignore`.
            """
        )


if __name__ == "__main__":
    main()
