# Guida correzione errore Tkinter su Streamlit Cloud

## Errore visto nello screenshot

```text
ImportError: This app has encountered an error
File "FinancePlus_360.py", line 29, in <module>
    import tkinter as tk
```

## Causa

`tkinter` serve per creare finestre desktop. Streamlit Cloud non apre finestre desktop: esegue app web nel browser. Per questo il file desktop non puo' essere usato come main file su Streamlit Cloud.

## Soluzione applicata

- Il file root `FinancePlus_360.py` e' stato sostituito con una vera app Streamlit.
- La versione desktop originale e' stata spostata in:

```text
desktop/FinancePlus_360_DESKTOP_TKINTER.py
```

## Cosa impostare in Streamlit Cloud

Nel campo **Main file path** inserire:

```text
FinancePlus_360.py
```

oppure:

```text
streamlit_app.py
```

## Password email

Usare password app/IMAP. Non committare password nel repository GitHub.
