import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 1. SEITENKONFIGURATION (Optimiert für Vollbild)
st.set_page_config(page_title="ABUS Batteriecheck", page_icon="🔋", layout="wide")

# CSS für Vollbild-Modus auf dem iPhone (blendet Browser-Leisten besser aus)
st.markdown("""
    <meta name="apple-mobile-web-app-capable" content="yes">
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display:none;}
    </style>
    """, unsafe_allow_html=True)

# 2. TITEL
st.title("🔋 ABUS Batteriecheck")

# --- VERBINDUNG & DATEN (Mit Turbo-Caching) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600) # Speichert Daten für 10 Minuten für schnelles Laden am Handy
def load_data():
    return conn.read(spreadsheet=st.secrets.get("spreadsheet"), ttl=0)

df = load_data()

COL_NAME = "Sender Name"
COL_ORT = "Standort"
COL_LETZTER = "Letzter Batteriewechsel"
COL_NAECHSTER = "Nächster Wechsel (geplant)"
COL_VERMERK = "Vermerke (z.B. Batterie)"
COL_STATUS = "Status"

# Grundstruktur sicherstellen
if df is None or df.empty or COL_NAME not in df.columns:
    df = pd.DataFrame(columns=[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_VERMERK, COL_STATUS])

# Datumsformate vorbereiten
df[COL_LETZTER] = pd.to_datetime(df[COL_LETZTER], errors='coerce').dt.date
df[COL_NAECHSTER] = pd.to_datetime(df[COL_NAECHSTER], errors='coerce').dt.date

# --- AUTOMATISCHE ERGÄNZUNG FÜR LEERE FELDER ---
# Wenn 'Letzter Wechsel' da ist, aber 'Nächster Wechsel' fehlt: Berechne +547 Tage
maske = df[COL_LETZTER].notnull() & df[COL_NAECHSTER].isnull()
df.loc[maske, COL_NAECHSTER] = df.loc[maske, COL_LETZTER] + timedelta(days=547)

df_clean = df.dropna(subset=[COL_NAME]).copy()
df_clean = df_clean[df_clean[COL_NAME].astype(str).str.lower() != "none"]

# Hilfsfunktionen
def format_date(d):
    return d.strftime('%d.%m.%Y') if pd.notnull(d) and hasattr(d, 'strftime') else ""

def style_status(row):
    h = datetime.now().date()
    n = row[COL_NAECHSTER]
    if pd.isna(n): return [''] * len(row)
    if n < heute: # Überfällig
        return ['background-color: #ffcccc; color: black; font-weight: bold'] * len(row)
    elif n < heute + timedelta(days=30): # Bald fällig
        return ['background-color: #fff3cd; color: black; font-weight: bold'] * len(row)
    else: # OK
        return ['background-color: #d4edda; color: black'] * len(row)

# --- DASHBOARD ---
heute = datetime.now().date()
if not df_clean.empty:
    df_aktuell_check = df_clean.sort_values(by=COL_LETZTER, ascending=False).drop_duplicates(subset=[COL_NAME])
    kritisch = len(df_aktuell_check[df_aktuell_check[COL_NAECHSTER] < heute])
    bald = len(df_aktuell_check[(df_aktuell_check[COL_NAECHSTER] >= heute) & (df_aktuell_check[COL_NAECHSTER] < heute + timedelta(days=30))])

    c1, c2, c3 = st.columns(3)
    if kritisch > 0: c1.error(f"⚠️ {kritisch} Sender überfällig!")
    else: c1.success("✅ Alle Batterien OK")
    if bald > 0: c2.warning(f"🔔 {bald} bald fällig")
    c3.metric("Sender gesamt", len(df_aktuell_check))

st.markdown("---")

# --- EINGABE ---
with st.expander("➕ Neuen Batteriewechsel registrieren"):
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        n_in = col1.text_input("Sender Name (z.B. Z202)").strip()
        d_in = col2.date_input("Wechseldatum", heute, format="DD.MM.YYYY")
        
        b_ort = ""
        if n_in and not df_clean.empty:
            t = df_clean[df_clean[COL_NAME].astype(str) == n_in]
            if not t.empty:
                lo = t.iloc[-1][COL_ORT]
                if pd.notnull(lo) and str(lo).lower() != "nan": b_ort = str(lo)
        
        o_in = st.text_input("Standort (z.B. Erdgeschoss)", value=b_ort)
        v_in = st.text_input("Vermerke (z.B. CR2032)")
        
        if st.form_submit_button("Speichern"):
            if n_in:
                naechster = d_in + timedelta(days=547)
                new_row = pd.DataFrame([{COL_NAME: n_in, COL_ORT: o_in, COL_LETZTER: d_in, COL_NAECHSTER: naechster, COL_VERMERK: v_in, COL_STATUS: "OK"}])
                df_to_save = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=df_to_save)
                st.cache_data.clear() # Cache leeren, damit neue Daten sofort sichtbar sind
                st.success("Gespeichert!")
                st.rerun()
            else:
                st.error("Bitte einen Namen für den Sender eingeben.")

# --- ANZEIGE MIT STANDORT-FILTER ---
if not df_clean.empty:
    st.subheader("📡 Aktueller Status")
    
    alle_standorte = sorted(df_clean[COL_ORT].dropna().unique())
    filter_ort = st.selectbox("Nach Standort filtern:", ["Alle Standorte"] + alle_standorte)
    
    df_aktuell = df_clean.sort_values(by=[COL_ORT, COL_LETZTER], ascending=[True, False]).drop_duplicates(subset=[COL_NAME])
    
    if filter_ort != "Alle Standorte":
        df_aktuell = df_aktuell[df_aktuell[COL_ORT] == filter_ort]

    st.dataframe(
        df_aktuell.style.apply(style_status, axis=1).format({COL_LETZTER: format_date, COL_NAECHSTER: format_date}),
        use_container_width=True, hide_index=True
    )

    csv = df_aktuell.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Liste für PDF-Druck exportieren (CSV)", csv, f"ABUS_Check_{heute}.csv", "text/csv")
    
    # --- HISTORIE ---
    st.markdown("---")
    with st.expander("🕒 Historie & Verlauf (pro Sender filterbar)", expanded=False):
        alle_sender = sorted(df_clean[COL_NAME].unique())
        filter_sender = st.selectbox("Sender auswählen:", ["Alle Sender anzeigen"] + alle_sender)
        
        df_hist = df_clean.sort_values(by=COL_LETZTER, ascending=False).copy()
        if filter_sender != "Alle Sender anzeigen":
            df_hist = df_hist[df_hist[COL_NAME] == filter_sender]
            
        df_hist[COL_LETZTER] = df_hist[COL_LETZTER].apply(format_date)
        df_hist[COL_NAECHSTER] = df_hist[COL_NAECHSTER].apply(format_date)
        
        st.table(df_hist[[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_VERMERK]])
else:
    st.info("Noch keine Daten vorhanden. Nutze das Formular oben!")
