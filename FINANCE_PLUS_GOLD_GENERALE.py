"""Entry point ufficiale di FINANCE_PLUS_GOLD_GENERALE."""

from __future__ import annotations

import hmac
import os

import streamlit as st

from FinancePlus_360 import (
    AppConfig,
    init_state,
    render_accounts_editor,
    render_config_panel,
    render_connection_tests,
    render_download,
    render_save_load,
)
from gold_workspace import APP_NAME, Hooks, render_workspace
from platinum_clients_v2 import render_clients_section


def _configured_password() -> str:
    try:
        if "FINANCEPLUS_APP_PASSWORD" in st.secrets:
            return str(st.secrets["FINANCEPLUS_APP_PASSWORD"])
    except Exception:
        pass
    return os.getenv("FINANCEPLUS_APP_PASSWORD", "")


def _require_access() -> None:
    expected = _configured_password()
    if not expected or st.session_state.get("gold_authenticated"):
        return
    st.markdown("# FINANCE_PLUS_GOLD_GENERALE")
    st.caption("Accesso riservato")
    entered = st.text_input("Password", type="password", key="gold_login_password")
    if st.button("Accedi", type="primary"):
        if hmac.compare_digest(entered, expected):
            st.session_state["gold_authenticated"] = True
            st.rerun()
        else:
            st.error("Password non corretta.")
    st.stop()


def main() -> None:
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="🏦",
        layout="wide",
        initial_sidebar_state="collapsed",
        menu_items={"About": "FINANCE_PLUS_GOLD_GENERALE — Finance & Credit Intelligence"},
    )
    _require_access()
    init_state()
    cfg: AppConfig = st.session_state.cfg
    hooks = Hooks(
        mail_download_renderer=render_download,
        accounts_renderer=render_accounts_editor,
        config_renderer=render_config_panel,
        connection_renderer=render_connection_tests,
        save_load_renderer=render_save_load,
        airtable_renderer=render_clients_section,
    )
    render_workspace(cfg, hooks)


if __name__ == "__main__":
    main()
