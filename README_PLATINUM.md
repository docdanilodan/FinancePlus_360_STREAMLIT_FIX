# 💎 F_P_DIAMOND / F_P_PLATINUM V_1.1

Workspace Streamlit evoluto di FinancePlus 360.

## Moduli principali

- Dashboard operativa
- Clienti / Aziende 360 con Airtable
- Pratiche e workflow
- Archivio documentale
- Email multi-account Gmail + Aruba via IMAP
- Analisi creditizie
- Centrale Rischi e Conti Correnti
- Business Plan
- Report e riepiloghi PDF/CSV
- Scadenzario e impostazioni

## Avvio locale

```bash
streamlit run streamlit_app.py
```

`streamlit_app.py` è l'entrypoint consigliato e richiama `FinancePlus_PLATINUM.main`.

## Streamlit Community Cloud

Configurazione consigliata:

```text
Repository: docdanilodan/FinancePlus_360_STREAMLIT_FIX
Branch: main
Main file path: streamlit_app.py
```

In alternativa `FinancePlus_PLATINUM.py` può essere usato come entrypoint diretto.

### Secrets obbligatori per Airtable

Inserire esclusivamente in **Streamlit Community Cloud > App settings > Secrets**:

```toml
AIRTABLE_TOKEN = "pat_xxxxxxxxx"
AIRTABLE_BASE_ID = "appoNJtS64JIcZUhT"
```

### Secrets email opzionali

Per inizializzare automaticamente Gmail e le caselle Aruba usare la sezione `[financeplus_mail]` descritta in `.streamlit/secrets.example.toml`.

Non salvare password, token o un vero `.streamlit/secrets.toml` nel repository pubblico.

## Dipendenze

Le dipendenze Cloud sono dichiarate in `requirements.txt` alla radice del repository.

## Sicurezza

Il repository contiene solo configurazioni non segrete e file di esempio. `.gitignore` esclude i segreti Streamlit, `.env`, configurazioni email locali e output scaricati.
