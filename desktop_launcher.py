"""Launcher desktop usato per costruire l'eseguibile Windows."""

from __future__ import annotations

import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path


def _bundle_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def _user_data_dir() -> Path:
    base = Path(os.getenv("APPDATA") or Path.home())
    target = base / "FINANCE_PLUS_GOLD_GENERALE"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> None:
    os.environ.setdefault("FINANCEPLUS_DATA_DIR", str(_user_data_dir()))
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    port = _free_port()
    app_path = _bundle_dir() / "streamlit_app.py"
    if not app_path.exists():
        raise FileNotFoundError(f"File applicazione non trovato: {app_path}")
    url = f"http://127.0.0.1:{port}"
    threading.Timer(2.0, lambda: webbrowser.open(url)).start()
    sys.argv = [
        "streamlit", "run", str(app_path),
        "--server.headless=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
    ]
    from streamlit.web import cli as stcli

    raise SystemExit(stcli.main())


if __name__ == "__main__":
    main()
