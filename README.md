# FINANCE_PLUS_GOLD_GENERALE

Piattaforma Streamlit unificata per gestione clienti, fascicoli documentali, pratiche finanziarie, analisi di bilancio, Centrale Rischi, conti correnti, rating gestionale, business plan e dossier bancari PDF.

## Avvio rapido

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Su Streamlit Community Cloud impostare **Main file path** su `streamlit_app.py`.

## Moduli operativi

| Modulo | Funzioni principali |
|---|---|
| Dashboard | Clienti, pratiche, importi richiesti, documenti, scadenze e portafoglio rating |
| Clienti 360 | Ricerca, creazione e modifica anagrafica; P.IVA e C.F. facoltativi; fascicolo e completezza |
| Pratiche | Pipeline, istituto, importo, stato, priorità, completezza, probabilità e prossima azione |
| Documenti | Upload multiplo, classificazione, SHA-256 anti-duplicati, ricerca, anteprima e download |
| Bilanci/KPI | Ricavi, EBITDA, PFN, DSCR, PFN/EBITDA, patrimonializzazione, liquidità e trend |
| Centrale Rischi | Accordato, utilizzato, scaduto, past due, garanzie, intermediari e anomalie |
| Conti correnti | Import CSV/XLSX, mapping colonne, entrate/uscite, flusso netto, copertura e saldi |
| Rating/MCC | Score gestionale 0–100, classe AAA–D, componenti, punti di forza e criticità |
| Business Plan | Previsioni fino a 10 anni, CFADS, DSCR, PFN, scenari e CSV scaricabile |
| Mandati e compensi | Incarichi, percentuali, minimi, acconti, residui e scadenze |
| Banche e factoring | Offerte, TAN, TAEG, durata, garanzie, rata stimata e confronto condizioni |
| Email | Gmail/Aruba IMAP multi-account, filtri mittenti, acquisizione allegati e ZIP |
| Scadenzario | Attività per cliente, priorità, stato, scadute e previste oggi |
| Report | Dossier bancario PDF con anagrafica, KPI, CR, pratiche e completezza documentale |
| Airtable Live | Consultazione anagrafiche collegate tramite token protetto |
| Automazioni e sicurezza | Registro automazioni, password applicativa, audit log e backup ZIP |

## Versione Windows `.exe`

La pipeline **Build Windows EXE** genera automaticamente `FINANCE_PLUS_GOLD_GENERALE.exe` su un runner Windows reale. Il file è pubblicato come artifact GitHub `FINANCE_PLUS_GOLD_GENERALE_WINDOWS`.

L'eseguibile avvia un server locale e apre il programma nel browser predefinito. Database e documenti sono salvati nella cartella utente `%APPDATA%\FINANCE_PLUS_GOLD_GENERALE`.

Per ricostruire manualmente l'eseguibile su Windows:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
pyinstaller --noconfirm --clean FINANCE_PLUS_GOLD_GENERALE.spec
```

In alternativa, senza `.exe`, fare doppio clic su `AVVIA_FINANCE_PLUS_GOLD_GENERALE.bat`.

## Persistenza

Il database predefinito è SQLite e viene creato in `data/financeplus_gold_generale.sqlite3`; i file sono archiviati in `data/documenti/Cliente/Anno/Categoria`. La directory `data/` è esclusa da Git.

Per usare un percorso persistente personalizzato:

```bash
export FINANCEPLUS_DATA_DIR=/percorso/persistente/financeplus
```

Su hosting effimero occorre montare uno storage persistente oppure utilizzare un backend esterno. Airtable resta un'integrazione opzionale, non un requisito per avviare l'app.

## Airtable

Copiare `.streamlit/secrets.example.toml` nelle impostazioni protette di Streamlit e valorizzare:

```toml
AIRTABLE_TOKEN = "pat_..."
AIRTABLE_BASE_ID = "app_..."
FINANCEPLUS_APP_PASSWORD = "password-riservata"
```

Non inserire mai token o password in file pubblici.

## Email IMAP

- Gmail: `imap.gmail.com`, porta 993 SSL, password per app.
- Aruba: `imap.aruba.com`, porta 993 SSL, credenziali della casella.
- La cancellazione delle email è disattivata per impostazione predefinita.
- La configurazione locale `financeplus_mail_config.local.json` è esclusa dal repository.

## Rating e avvertenze

Lo score è uno strumento gestionale interno basato su soglie trasparenti per DSCR, PFN/EBITDA, EBITDA margin, equity ratio, current ratio, leverage e Centrale Rischi. Non replica i modelli proprietari di MCC, CRIF o degli istituti di credito e non costituisce promessa di finanziamento.

## Test

```bash
python -m compileall -q .
pytest -q
```

La pipeline GitHub Actions esegue compilazione, controllo degli errori bloccanti e test su Python 3.10, 3.11 e 3.12.

## Entry point e compatibilità

- `streamlit_app.py`: entry point per Streamlit Cloud.
- `FINANCE_PLUS_GOLD_GENERALE.py`: applicazione ufficiale.
- `FinancePlus_PLATINUM.py`: wrapper di compatibilità con il nome precedente.
- `FinancePlus_360.py`: motore email cloud-safe preesistente.
- `desktop/`: versione storica Tkinter, esclusa dai controlli CI.
