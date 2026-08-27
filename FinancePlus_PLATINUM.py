"""F_P_DIAMOND V_1.1 - Streamlit entrypoint.

Versione evoluta di FinancePlus 360 con sezione Clienti collegata ad Airtable.
La versione originale resta intatta in FinancePlus_360.py.
"""
from __future__ import annotations

import streamlit as st

from FinancePlus_360 import (
    AppConfig,
    APP_VERSION as LEGACY_APP_VERSION,
    init_state,
    render_accounts_editor,
    render_config_panel,
    render_connection_tests,
    render_download,
    render_save_load,
)
from platinum_clients_v2 import render_clients_section

APP_NAME = "F_P_DIAMOND V_1.1"
APP_VERSION = "1.1"


def render_sidebar() -> None:
    with st.sidebar:
        st.title("💎 F_P_DIAMOND V_1.1")
        st.caption("Finance & Credit Intelligence Workspace")
        st.markdown("---")
        st.markdown("**Moduli attivi**")
        st.markdown("- 👥 Clienti Airtable\n- 📩 Email & allegati\n- 🗂️ Dossier collegati\n- 📊 Analisi creditizie\n- 📄 Riepilogo documenti PDF")
        st.markdown("---")
        st.caption(f"DIAMOND V_{APP_VERSION} · Core {LEGACY_APP_VERSION}")


def render_home() -> None:
    st.header("💎 F_P_DIAMOND V_1.1")
    st.markdown(
        "Workspace unico per **clienti, pratiche, documenti, email e analisi creditizie**. "
        "La sezione Clienti legge direttamente il CRM Airtable, apre l'anagrafica completa dentro Streamlit "
        "e consente di visualizzare e scaricare il riepilogo PDF dei documenti collegati."
    )
    c1, c2, c3 = st.columns(3)
    c1.success("👥 **Clienti**\n\nRicerca live su Airtable")
    c2.info("📩 **Email**\n\nDownload e archiviazione allegati")
    c3.info("📄 **Riepilogo PDF**\n\nTabella documentale per cliente")
    st.markdown("### Accesso rapido")
    st.write("Apri **👥 Clienti**, cerca il cliente, seleziona la sua anagrafica e usa i pulsanti del riepilogo documentale.")


def render_settings(cfg: AppConfig) -> None:
    st.header("⚙️ Configurazione email")
    render_accounts_editor(cfg)
    render_config_panel(cfg)
    render_save_load(cfg)
    render_connection_tests(cfg)


def render_guide() -> None:
    st.header("📘 Guida rapida")
    st.markdown(
        """
### Clienti Airtable
1. Configura `AIRTABLE_TOKEN` nei **Secrets** di Streamlit Cloud.
2. Apri **👥 Clienti**.
3. Cerca per ragione sociale, P.IVA, codice fiscale, PEC o email.
4. Seleziona il cliente: l'anagrafica si apre nella stessa app.
5. Usa le schede **Pratiche**, **Documenti**, **Email** e **Analisi Creditizie** per consultare i record collegati.
6. Nella sezione **Riepilogo documenti cliente** usa **Visualizza riepilogo documenti** oppure **Scarica riepilogo PDF**.

### Contenuto del PDF documentale
Il PDF riporta tutti i record documentali collegati al cliente in Airtable con tipo, esercizio, data, nome documento, origine, stato verifica, sintesi IA e link Drive quando disponibile.

### Secrets richiesti
```toml
AIRTABLE_TOKEN = "pat_xxxxxxxxx"
AIRTABLE_BASE_ID = "appoNJtS64JIcZUhT"
```
Il token **non deve essere salvato su GitHub**.

### Email
Il modulo email mantiene le funzioni della versione FinancePlus 360: account multipli, filtri mittente, anti-duplicati, ZIP ed estrazione anagrafica.
        """
    )


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="💎", layout="wide")
    init_state()
    cfg: AppConfig = st.session_state.cfg
    render_sidebar()

    tab_home, tab_clients, tab_mail, tab_settings, tab_guide = st.tabs(
        ["🏠 Home", "👥 Clienti", "📩 Email / Allegati", "⚙️ Configurazione", "📘 Guida"]
    )
    with tab_home:
        render_home()
    with tab_clients:
        render_clients_section()
    with tab_mail:
        st.header("📩 Email e allegati")
        render_download(cfg)
    with tab_settings:
        render_settings(cfg)
    with tab_guide:
        render_guide()


if __name__ == "__main__":
    main()
