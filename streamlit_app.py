import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 1. Browsertab Name
st.set_page_config(page_title="ABUS Batteriecheck", page_icon="🔋", layout="wide")

# 2. Hauptüberschrift
st.title("🔋 ABUS Batteriecheck")

# --- NUTZERIDENTIFIKATION ---
st.sidebar.markdown("### 👤 Nutzerprofil")
st.sidebar.image("https://www.gstatic.com/images/branding/product/2x/keep_2020q4_48dp.png", width=80)
st.sidebar.info("Verwaltung der ABUS Funk-Sender")

# --- VERBINDUNG & DATEN (ttl=0 für Echtzeit) ---
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0) 

COL_NAME = "Sender Name"
COL_ORT = "Standort"
COL_LETZTER = "Letzter Batteriewechsel"
COL_NAECHSTER = "Nächster Wechsel (geplant)"
COL_VERMERK = "Vermerke (z.B. Batterie)"
COL_STATUS = "Status"

if df is None or df.empty or COL_NAME not in df.columns:
    df = pd.DataFrame(columns=[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_VERMERK, COL_STATUS])

# Datumsformate für Logik vorbereiten
df[COL_LETZTER] = pd.to_datetime(df[COL_LETZTER], errors='coerce').dt.date
df[COL_NAECHSTER] = pd.to_datetime(df[COL_NAECHSTER], errors='coerce').dt.date
df_clean = df.dropna(subset=[COL_NAME]).copy()
df_clean = df_clean[df_clean[COL_NAME].astype(str).str.lower() != "none"]

# Hilfsfunktionen für Anzeige
def format_date(d):
    return d.strftime('%d.%m.%Y') if pd.notnull(d) and hasattr(d, 'strftime') else ""

def style_status(row):
    h = datetime.now().date()
    n = row[COL_NAECHSTER]
    if pd.isna(n): return [''] * len(row)
    if n < h: return ['background-color: #ffcccc'] * len(row) # Rot
    elif n < h + timedelta(days=30): return ['background-color: #fff3cd'] * len(row) # Gelb
    else: return ['background-color: #d4edda'] * len(row) # Grün

# --- DASHBOARD ---
if not df_clean.empty:
    heute = datetime.now().date()
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
with st.expander("➕ Neuen Wechsel registrieren"):
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        n_in = col1.text_input("Sender Name").strip()
        d_in = col2.date_input("Wechseldatum", heute, format="DD.MM.YYYY")
        
        b_ort = ""
        if n_in and not df_clean.empty:
            t = df_clean[df_clean[COL_NAME].astype(str) == n_in]
            if not t.empty:
                lo = t.iloc[-1][COL_ORT]
                if pd.notnull(lo) and str(lo).lower() != "nan": b_ort = str(lo)
        
        o_in = st.text_input("Standort", value=b_ort)
        v_in = st.text_input("Vermerke (z.B. CR2032)")
        if st.form_submit_button("Speichern"):
            naechster = d_in + timedelta(days=547)
            new_row = pd.DataFrame([{COL_NAME: n_in, COL_ORT: o_in, COL_LETZTER: d_in, COL_NAECHSTER: naechster, COL_VERMERK: v_in, COL_STATUS: "OK"}])
            df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=df)
            st.success("Gespeichert!")
            st.rerun()

# --- ANZEIGE MIT FARBEN ---
if not df_clean.empty:
    st.subheader("📡 Aktueller Status")
    df_aktuell = df_clean.sort_values(by=[COL_ORT, COL_LETZTER], ascending=[True, False]).drop_duplicates(subset=[COL_NAME])
    
    # Hier wird die Farblogik auf die Tabelle angewendet
    st.dataframe(
        df_aktuell.style.apply(style_status, axis=1).format({COL_LETZTER: format_date, COL_NAECHSTER: format_date}),
        use_container_width=True, hide_index=True
    )

    csv = df_aktuell.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Liste für PDF-Druck exportieren (CSV)", csv, f"ABUS_Check_{heute}.csv", "text/csv")
    
    with st.expander("🕒 Historie & Verlauf"):
        # Historie sortiert anzeigen
        df_hist = df_clean.sort_values(by=COL_LETZTER, ascending=False).copy()
        df_hist[COL_LETZTER] = df_hist[COL_LETZTER].apply(format_date)
        df_hist[COL_NAECHSTER] = df_hist[COL_NAECHSTER].apply(format_date)
        st.table(df_hist[[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_VERMERK]])
else:
    st.info("Noch keine Daten vorhanden.")
