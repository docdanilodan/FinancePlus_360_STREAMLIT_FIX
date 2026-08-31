"""F_P_PLATINUM V_1.1 - workspace professionale FinancePlus.

Integra il core FinancePlus 360, Airtable, email multi-account, archivio documentale,
analisi creditizie, scadenzario e reportistica in una navigazione unificata.
"""
from __future__ import annotations

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
from platinum_clients_v2 import render_clients_section
from platinum_workspace import Hooks, render_workspace

APP_NAME = "F_P_PLATINUM V_1.1"


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="💎", layout="wide", initial_sidebar_state="expanded")
    init_state()
    cfg: AppConfig = st.session_state.cfg
    hooks = Hooks(
        clients_renderer=render_clients_section,
        mail_download_renderer=render_download,
        accounts_renderer=render_accounts_editor,
        config_renderer=render_config_panel,
        connection_renderer=render_connection_tests,
        save_load_renderer=render_save_load,
    )
    render_workspace(cfg=cfg, hooks=hooks)


if __name__ == "__main__":
    main()
