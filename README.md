# FinancePlus 360 - GitHub / Streamlit FIX

Pacchetto corretto per risolvere l'errore Streamlit Cloud:

```text
ImportError: libtk... Python may not be configured for Tk
```

## File principali

| File | Uso |
|---|---|
| `FinancePlus_360.py` | App web Streamlit compatibile Cloud, senza Tkinter |
| `streamlit_app.py` | Wrapper alternativo per Streamlit Cloud |
| `desktop/FinancePlus_360_DESKTOP_TKINTER.py` | Versione desktop originale Tkinter, da usare solo su PC |
| `requirements.txt` | Dipendenze per Streamlit Cloud |
| `.streamlit/secrets.example.toml` | Esempio configurazione sicura password |

## Avvio locale web

```bash
pip install -r requirements.txt
streamlit run FinancePlus_360.py
```

Su Windows puoi usare direttamente:

```bat
RUN_LOCAL_WINDOWS.bat
```

## Avvio desktop originale

```bat
RUN_DESKTOP_WINDOWS.bat
```

## Configurazione su Streamlit Cloud

1. Carica questa cartella su GitHub.
2. Vai su Streamlit Cloud.
3. Imposta **Main file path** su:

```text
FinancePlus_360.py
```

oppure:

```text
streamlit_app.py
```

4. Inserisci le password app/IMAP dalla schermata dell'app oppure in **Settings > Secrets**.
5. Premi **Testa account attivi**.
6. Premi **Scarica allegati/email**.
7. Scarica lo ZIP generato.

## Funzioni incluse

- 3 account preconfigurati:
  - Gmail personale
  - `pratiche@financeplus.tech`
  - `d.dangelo@financeplus.tech`
- IMAP host/porta/cartella configurabili.
- Mittenti monitorati già caricati.
- Salvataggio `.eml` opzionale.
- Anti-duplicati su hash SHA-256.
- Archivio ZIP scaricabile.
- Struttura cliente/anno/mese.
- Cartella `_TEMP_DA_ABBINARE` per documenti non riconosciuti.
- `ANAGRAFICA_CLIENTI_DA_MAIL.csv` generato automaticamente.
- Riepilogo tecnico `RIEPILOGO_DOWNLOAD.json`.

## Nota importante password

Non caricare mai su GitHub file con password reali. Il file:

```text
financeplus_mail_config.local.json
```

e il file:

```text
.streamlit/secrets.toml
```

sono esclusi dal `.gitignore`.
