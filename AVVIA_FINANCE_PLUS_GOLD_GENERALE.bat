@echo off
setlocal
cd /d "%~dp0"
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
endlocal
