# 💎 FinancePlus PLATINUM

Versione Streamlit evoluta di FinancePlus 360.

## Novità principale: 👥 Clienti Airtable

La sezione **Clienti** legge direttamente la base Airtable FinancePlus AI e consente di:

- cercare per ragione sociale, P.IVA, codice fiscale, PEC o email;
- aprire l'anagrafica senza uscire da Streamlit;
- vedere rating FinancePlus e ultimo bilancio;
- consultare pratiche collegate;
- consultare documenti collegati;
- consultare email collegate;
- consultare analisi creditizie collegate;
- aggiornare la cache Airtable dalla UI.

## Avvio

```bash
streamlit run FinancePlus_PLATINUM.py
```

Su Streamlit Community Cloud usare come **Main file path**:

```text
FinancePlus_PLATINUM.py
```

## Secrets

Aggiungere nelle impostazioni dell'app Streamlit:

```toml
AIRTABLE_TOKEN = "pat_xxxxxxxxx"
AIRTABLE_BASE_ID = "appoNJtS64JIcZUhT"
```

Non committare mai il token Airtable nel repository.

## Sicurezza

Il codice contiene solo gli ID non segreti della base e delle tabelle. Il PAT Airtable viene letto esclusivamente da Streamlit Secrets o dalla variabile ambiente `AIRTABLE_TOKEN`.
