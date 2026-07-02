@echo off
cd /d "%~dp0"
python -m pip install pypdf pillow reportlab
python desktop\FinancePlus_360_DESKTOP_TKINTER.py
pause
