from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Dict, List, Optional, Sequence
import streamlit as st

APP_BRAND = "F_P_PLATINUM"
APP_VERSION = "V_1.1"
NAV = ["Dashboard","Aziende","Pratiche","Documenti","Email","Analisi","Scadenzario","Report","Impostazioni"]
VIEWS: Dict[str,List[str]] = {
    "Dashboard":["Sintesi","Portafoglio","Alert e attività"],
    "Aziende":["Elenco","Anagrafica","Governance","Soci","Sedi","Contatti","Documenti","Airtable Live"],
    "Pratiche":["Pipeline","Calendario","Attività","Alert"],
    "Documenti":["Tutti","Visure","Bilanci","CR","Estratti conto","Contratti"],
    "Email":["Download operativo","Account","Mittenti e opzioni","Test connessioni","Salva configurazione"],
    "Analisi":["Sintesi","Bilanci","Centrale Rischi","Conti Correnti","MCC","Business Plan"],
    "Scadenzario":["Oggi","Settimana","Mese","Scadute"],
    "Report":["Dossier Bancario","Riepilogo Documenti","Report Creditizio","Business Plan"],
    "Impostazioni":["Airtable","Email IMAP","Sicurezza","Aspetto","Diagnostica"],
}

@dataclass(frozen=True)
class Hooks:
    clients_renderer: Optional[Callable[[],None]] = None
    mail_download_renderer: Optional[Callable[[Any],None]] = None
    accounts_renderer: Optional[Callable[[Any],None]] = None
    config_renderer: Optional[Callable[[Any],None]] = None
    connection_renderer: Optional[Callable[[Any],None]] = None
    save_load_renderer: Optional[Callable[[Any],None]] = None


def style() -> None:
    st.markdown("""<style>
    :root{--navy:#073f73;--blue:#155a93;--line:#dbe4ec;--muted:#6c7b8a}
    [data-testid=stHeader],[data-testid=stToolbar],footer{visibility:hidden;height:0}.block-container{padding-top:.55rem;max-width:100%}
    section[data-testid=stSidebar]{background:linear-gradient(180deg,var(--navy),#052f59)}section[data-testid=stSidebar] *{color:white}
    section[data-testid=stSidebar] label{padding:.5rem .4rem;border-radius:7px;margin:2px 0}.fp-brand{font-weight:800;letter-spacing:.08em;font-size:1.2rem}.fp-ver{font-size:.68rem;opacity:.75;margin-bottom:1rem}
    .fp-top{background:linear-gradient(90deg,var(--navy),#0b568e);color:white;padding:11px 17px;border-radius:7px;font-size:1.13rem;font-weight:800;margin-bottom:.7rem}
    .fp-card{background:white;border:1px solid var(--line);border-radius:9px;padding:13px;min-height:88px}.fp-l{font-size:.71rem;color:#4d6073;font-weight:700;text-transform:uppercase}.fp-v{font-size:1.5rem;font-weight:800;margin-top:5px}.fp-n{font-size:.72rem;color:var(--muted);margin-top:4px}
    .fp-company{font-size:1.2rem;font-weight:800}.fp-pill{background:#e7f4ec;color:#2b6d4c;border-radius:999px;padding:3px 8px;font-size:.68rem;margin-left:7px}.fp-note{background:#f8fbfe;border:1px solid var(--line);border-left:4px solid #ba7937;border-radius:8px;padding:12px;color:#465c70;font-size:.82rem}
    .fp-table{width:100%;border-collapse:collapse;font-size:.77rem}.fp-table th{background:#f2f5f8;color:#3a5065;text-align:left;padding:9px;border-bottom:1px solid var(--line)}.fp-table td{padding:9px;border-bottom:1px solid #edf1f5;color:#30465a}
    div[role=radiogroup]{gap:.2rem}div[role=radiogroup] label{border:1px solid #d8e2ec;border-radius:7px;padding:.3rem .55rem;background:white}div[role=radiogroup] label:has(input:checked){background:#eef6ff;border-color:#83acd0}
    </style>""",unsafe_allow_html=True)


def q(name:str, default:str)->str:
    try:
        v=st.query_params.get(name,default); return str(v[0] if isinstance(v,list) else v)
    except Exception: return default


def table(headers:Sequence[str], rows:Sequence[Sequence[str]])->None:
    h="".join(f"<th>{x}</th>" for x in headers); b="".join("<tr>"+"".join(f"<td>{c}</td>" for c in r)+"</tr>" for r in rows)
    st.markdown(f'<table class="fp-table"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>',unsafe_allow_html=True)


def card(label:str,value:str,note:str="")->None:
    st.markdown(f'<div class="fp-card"><div class="fp-l">{label}</div><div class="fp-v">{value}</div><div class="fp-n">{note}</div></div>',unsafe_allow_html=True)


def chrome()->tuple[str,str]:
    with st.sidebar:
        st.markdown(f'<div class="fp-brand">{APP_BRAND}</div><div class="fp-ver">{APP_VERSION}</div>',unsafe_allow_html=True)
        req=q("page",NAV[0]); page=st.radio("Nav",NAV,index=NAV.index(req) if req in NAV else 0,label_visibility="collapsed")
        st.markdown("<div style='height:1rem'></div>",unsafe_allow_html=True); st.caption("? Help"); st.caption("↪ Esci")
    reqv=q("view",VIEWS[page][0]); view=st.radio("Vista",VIEWS[page],index=VIEWS[page].index(reqv) if reqv in VIEWS[page] else 0,horizontal=True,label_visibility="collapsed",key=f"v_{page}")
    return page,view


def top(title:str)->None: st.markdown(f'<div class="fp-top">{title}</div>',unsafe_allow_html=True)
def company()->None: st.markdown('<div class="fp-company">ALFA INDUSTRIA S.R.L.<span class="fp-pill">Cliente attivo</span></div><div class="fp-n">P. IVA 12345678901 · Codice fiscale 12345678901 · REA MI-1234567</div>',unsafe_allow_html=True)


def dashboard(view:str)->None:
    top("Dashboard - Finance & Credit Intelligence"); cols=st.columns(4)
    for col,x in zip(cols,[("Clienti attivi","72","+4 nel mese"),("Pratiche attive","12","€ 1,85 mln richiesti"),("Completezza media","86%","Dossier documentali"),("Rating medio","BBB","Portafoglio PMI")]):
        with col: card(*x)
    if view=="Portafoglio": st.bar_chart({"Clienti":{"AA":8,"A":14,"BBB":26,"BB":15,"B":7,"CCC":2}}); return
    rows=[["ALFA INDUSTRIA","Chirografario","€ 250.000","Istruttoria","15/09/2026"],["OMEGA","Anticipo fatture","€ 150.000","Delibera","14/09/2026"],["KAPPA","Mutuo","€ 350.000","Erogazione","18/09/2026"]]
    if view=="Sintesi": table(["Cliente","Pratica","Importo","Fase","Prossima azione"],rows)
    else: table(["Priorità","Tipo","Cliente","Descrizione","Scadenza"],[["Alta","Documento","ALFA INDUSTRIA","CR aggiornata","Oggi"],["Alta","Pratica","OMEGA","Riscontro banca","Domani"],["Media","Email","KAPPA","Integrare allegati","02/09/2026"]])


def aziende(view:str,h:Hooks)->None:
    top("Scheda Azienda 360")
    if view=="Airtable Live" and h.clients_renderer: h.clients_renderer(); return
    if view=="Elenco":
        st.text_input("Cerca azienda",placeholder="Ragione sociale, P.IVA, CF, PEC..."); table(["Azienda","P.IVA","Rating","Pratiche","Documenti"],[["ALFA INDUSTRIA S.R.L.","12345678901","BBB","2","29"],["BETA MECCANICA S.P.A.","10987654321","A","1","18"],["OMEGA S.R.L.","01234567890","BBB","3","24"]]); return
    company()
    maps={
    "Anagrafica":(["Dato","Valore"],[["Denominazione","ALFA INDUSTRIA S.R.L."],["P. IVA","12345678901"],["Codice fiscale","12345678901"],["REA","MI-1234567"],["Forma giuridica","S.r.l."],["Capitale sociale","€ 100.000 i.v."],["ATECO","28.99.00"],["PEC","alfaindustria@pec.it"],["Sede legale","Milano"]]),
    "Governance":(["Ruolo","Nominativo","Dal","Note"],[["Amministratore unico","Mario Rossi","15/05/2025","Pieni poteri"],["Revisore","Studio Bianchi","01/01/2026","Revisione legale"]]),
    "Soci":(["Socio","Quota","Valore","Tipo"],[["Mario Rossi","70%","€ 70.000","Persona fisica"],["Holding Alfa S.r.l.","30%","€ 30.000","Società"]]),
    "Sedi":(["Tipo","Indirizzo","Comune","Uso"],[["Legale","Via dell'Industria 10","Milano","Direzione"],["Operativa","Via Meccanica 4","Monza","Produzione"]]),
    "Contatti":(["Tipo","Riferimento","Contatto"],[["Email","Amministrazione","amministrazione@alfaindustria.it"],["PEC","Società","alfaindustria@pec.it"],["Telefono","Direzione","+39 02 1234567"]]),
    "Documenti":(["Documento","Categoria","Data","Stato"],[["Visura camerale storica.pdf","Visura","10/05/2026","Presente"],["Bilancio 2025.pdf","Bilancio","30/04/2026","Presente"],["Centrale Rischi.pdf","CR","08/08/2026","Presente"]])}
    if view in maps: table(*maps[view])
    else: st.info("Vista live disponibile con Airtable configurato.")


def pratiche(view:str)->None:
    top("Pratiche e Scadenze"); c1,c2,c3=st.columns(3)
    with c1: card("Pratiche attive","12","4 in istruttoria")
    with c2: card("Scadenze oggi","3","1 priorità alta")
    with c3: card("Importo richiesto","€ 1,85 mln","Portafoglio corrente")
    if view=="Pipeline": table(["Fase","Cliente","Importo","Istruttore"],[["Istruttoria","ALFA INDUSTRIA","€ 250.000","M. Rossi"],["Integrazione","BETA MECCANICA","€ 750.000","L. Bianchi"],["Delibera","OMEGA","€ 150.000","M. Rossi"],["Erogazione","KAPPA","€ 350.000","A. Verdi"]])
    elif view=="Calendario": table(["Data","Ora","Cliente","Evento"],[["31/08","09:30","ALFA INDUSTRIA","Call documenti"],["31/08","15:00","OMEGA","Delibera attesa"],["01/09","11:00","KAPPA","Firma contratto"]])
    elif view=="Attività": table(["Stato","Attività","Cliente","Scadenza"],[["Da fare","Richiedere CR","ALFA INDUSTRIA","31/08"],["In corso","Analisi EC","BETA MECCANICA","01/09"],["Completata","Dossier banca","OMEGA","30/08"]])
    else: table(["Livello","Cliente","Alert","Azione"],[["Alto","ALFA INDUSTRIA","4 documenti mancanti","Sollecito"],["Alto","BETA MECCANICA","CR > 60 giorni","Aggiornare"],["Medio","OMEGA","Delibera domani","Follow-up"]])


def documenti(view:str)->None:
    top("Archivio Documentale IA"); c1,c2=st.columns([3,1]); c1.text_input("Cerca documento");
    with c2: card("Completezza dossier","86%","25/29 presenti")
    rows=[["Visura camerale storica.pdf","Visure","10/05/2026","Presente"],["Bilancio Esercizio 2025.pdf","Bilanci","30/04/2026","Presente"],["Centrale Rischi BI.pdf","CR","08/08/2026","Presente"],["Estratto conto 12 mesi.pdf","Estratti conto","07/08/2026","Presente"],["Contratto leasing.pdf","Contratti","15/03/2026","Presente"]]
    if view!="Tutti": rows=[r for r in rows if r[1]==view]
    table(["Nome documento","Categoria","Data","Stato"],rows); st.button("Carica documenti"); st.button("Analizza con IA")


def email_page(view:str,cfg:Any,h:Hooks)->None:
    top("Email e Allegati - Multi Account")
    callbacks={"Download operativo":h.mail_download_renderer,"Account":h.accounts_renderer,"Mittenti e opzioni":h.config_renderer,"Test connessioni":h.connection_renderer,"Salva configurazione":h.save_load_renderer}
    if callbacks.get(view): callbacks[view](cfg); return
    table(["Account","Host","Porta","Stato"],[["Gmail principale","imap.gmail.com","993","Pronto"],["D.Dangelo@financeplus.tech","imap.aruba.com","993","Pronto"],["Pratiche@financeplus.tech","imap.aruba.com","993","Pronto"]])


def analisi(view:str)->None:
    top("Dossier Bancario e Analisi Creditizia"); company()
    if view=="Sintesi":
        cols=st.columns(4)
        for col,x in zip(cols,[("Ricavi","€ 5,8 mln","2025"),("EBITDA","14,2%","2025"),("DSCR","1,42x","Forward"),("PFN/EBITDA","2,1x","2025")]):
            with col: card(*x)
        st.line_chart({"Ricavi":[3.6,4.2,4.9,5.5,5.8],"EBITDA":[.6,.8,1,1.2,1.4],"PFN":[1.7,2,2.4,2.8,3.2]}); return
    maps={"Bilanci":(["Voce","2023","2024","2025"],[["Ricavi","€ 4,9 mln","€ 5,5 mln","€ 5,8 mln"],["EBITDA","€ 0,7 mln","€ 0,8 mln","€ 0,82 mln"],["PFN","€ 1,6 mln","€ 1,7 mln","€ 1,72 mln"]]),"Centrale Rischi":(["Intermediario","Forma tecnica","Accordato","Utilizzato"],[["Banca A","Autoliquidante","€ 300.000","€ 210.000"],["Banca B","A revoca","€ 180.000","€ 120.000"]]),"Conti Correnti":(["Indicatore","Valore","Giudizio"],[["Entrate 12m","€ 6,1 mln","Regolari"],["Saldo medio","€ 182.000","Positivo"],["Sconfinamenti","2","Limitati"]]),"MCC":(["Indicatore","Valore","Giudizio"],[["Leverage","3,1x","Adeguato"],["PFN/EBITDA","2,1x","Adeguato"],["DSCR","1,42x","Buono"],["Score","78/100","BBB"]]),"Business Plan":(["Anno","Ricavi","EBITDA","PFN","DSCR"],[["2026E","€ 6,2 mln","€ 0,95 mln","€ 1,8 mln","1,35x"],["2027","€ 7,1 mln","€ 1,18 mln","€ 1,65 mln","1,48x"],["2028","€ 8,0 mln","€ 1,40 mln","€ 1,42 mln","1,61x"]])}; table(*maps[view])


def scadenze(view:str)->None:
    top("Scadenzario"); table(["Quando","Cliente","Attività","Priorità"],[["Oggi","ALFA INDUSTRIA","CR aggiornata","Alta"],["Domani","OMEGA","Follow-up delibera","Alta"],["02/09","KAPPA","Firma contratto","Media"]])


def report(view:str)->None:
    top("Reportistica"); st.markdown(f'<div class="fp-note"><b>{view}</b><br>Generazione guidata del report FinancePlus con sezioni collegate a cliente, documenti e analisi.</div>',unsafe_allow_html=True); st.selectbox("Cliente",["ALFA INDUSTRIA S.R.L.","OMEGA S.R.L."]); st.selectbox("Formato",["PDF","PDF + CSV"]); st.button("Genera report")


def settings(view:str)->None:
    top("Impostazioni")
    if view=="Airtable": st.text_input("AIRTABLE_BASE_ID",value="appoNJtS64JIcZUhT"); st.text_input("AIRTABLE_TOKEN",type="password"); st.button("Verifica collegamento")
    elif view=="Email IMAP": table(["Account","Host","Porta","SSL"],[["Gmail","imap.gmail.com","993","Sì"],["D.Dangelo","imap.aruba.com","993","Sì"],["Pratiche","imap.aruba.com","993","Sì"]])
    elif view=="Sicurezza": st.checkbox("Usa solo Secrets",True); st.checkbox("Conferma eliminazione email",True); st.checkbox("Log senza credenziali",True)
    elif view=="Aspetto": st.selectbox("Tema",["FinancePlus Navy","Chiaro"]); st.selectbox("Densità",["Professionale","Compatta"])
    else: table(["Componente","Stato","Esito"],[["Core Streamlit","5.1 cloud-safe","OK"],["Airtable","REST API","OK"],["IMAP Gmail","SSL 993","OK"],["IMAP Aruba","SSL 993","OK"]]); st.button("Esegui diagnostica")


def render_workspace(cfg:Any=None,hooks:Optional[Hooks]=None)->None:
    style(); hooks=hooks or Hooks(); page,view=chrome()
    st.caption("Le viste non collegate a dati live usano valori dimostrativi; Airtable Live e il modulo Email usano le connessioni configurate.")
    if page=="Dashboard": dashboard(view)
    elif page=="Aziende": aziende(view,hooks)
    elif page=="Pratiche": pratiche(view)
    elif page=="Documenti": documenti(view)
    elif page=="Email": email_page(view,cfg,hooks)
    elif page=="Analisi": analisi(view)
    elif page=="Scadenzario": scadenze(view)
    elif page=="Report": report(view)
    else: settings(view)
