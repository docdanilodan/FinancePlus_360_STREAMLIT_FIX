# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules


streamlit_datas, streamlit_binaries, streamlit_hidden = collect_all("streamlit")
hidden = streamlit_hidden + collect_submodules("reportlab") + [
    "FINANCE_PLUS_GOLD_GENERALE",
    "FinancePlus_360",
    "gold_data",
    "gold_analytics",
    "gold_reports",
    "gold_workspace",
    "platinum_clients",
    "platinum_clients_v2",
    "platinum_pdf",
    "pandas",
    "pypdf",
    "openpyxl",
    "xlrd",
]

datas = streamlit_datas + [
    ("streamlit_app.py", "."),
    (".streamlit/config.toml", ".streamlit"),
]

a = Analysis(
    ["desktop_launcher.py"],
    pathex=[],
    binaries=streamlit_binaries,
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FINANCE_PLUS_GOLD_GENERALE",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
