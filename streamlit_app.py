import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 1. SEITENKONFIGURATION (Optimiert für Vollbild)
st.set_page_config(page_title="ABUS Batteriecheck", page_icon="🔋", layout="wide")

# CSS für Vollbild-Modus auf dem iPhone
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

# --- VERBINDUNG & DATEN ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def load_data():
    return conn.read(spreadsheet=st.secrets.get("spreadsheet"), ttl=0)

# Hilfsfunktionen für das Styling (Müssen vor der Nutzung definiert sein)
def format_date(d):
    return d.strftime('%d.%m.%Y') if pd.notnull(d) and hasattr(d, 'strftime') else ""

def style_status(row, heute):
    n = row["Nächster Wechsel (geplant)"]
    if pd.isna(n): return [''] * len(row)
    if n < heute: # Überfällig
        return ['background-color: #ffcccc; color: black; font-weight: bold'] * len(row)
    elif n < heute + timedelta(days=30): # Bald fällig
        return ['background-color: #fff3cd; color: black; font-weight: bold'] * len(row)
    else: # OK
        return ['background-color: #d4edda; color: black'] * len(row)

try:
    # 1. Daten laden
    df_raw = load_data()
    
    # 2. "None" entfernen
    df = df_raw.fillna("").astype(str).replace(["None", "nan", "NaN", "<NA>"], "")

    # Spaltennamen (sollten exakt so in Google stehen)
    COL_NAME = "Sender Name"
    COL_ORT = "Standort"
    COL_LETZTER = "Letzter Batteriewechsel"
    COL_NAECHSTER = "Nächster Wechsel (geplant)"
    COL_VERMERK = "Vermerke (z.B. Batterie)"

    # --- DATEN-SÄUBERUNG & SORTIERUNG (HIER EINFÜGEN) ---
    # Datumstypen fixen (für Berechnungen wichtig)
    df[COL_LETZTER] = pd.to_datetime(df[COL_LETZTER], errors='coerce').dt.date
    df[COL_NAECHSTER] = pd.to_datetime(df[COL_NAECHSTER], errors='coerce').dt.date
    
    # NUR DIE AKTUELLSTEN EINTRÄGE BEHALTEN:
    # Wir sortieren nach Name und Datum (neueste zuerst)
    # drop_duplicates wirft dann die alten, erledigten Wechsel von 2021 raus
    df_aktuell = df[df[COL_NAME] != ""].sort_values(by=[COL_NAME, COL_LETZTER], ascending=[True, False])
    df_aktuell = df_aktuell.drop_duplicates(subset=[COL_NAME])
    
    # Für die Anzeige: Die kritischen (überfälligen) nach oben sortieren
    df_view = df_aktuell.sort_values(by=[COL_NAECHSTER], ascending=True)
    # ---------------------------------------------------

    # --- DASHBOARD BERECHNUNG ---
    heute = datetime.now().date()
    # Wir rechnen nur mit der gefilterten Liste 'df_view'
    kritisch = len(df_view[df_view[COL_NAECHSTER] < heute])
    # ... Rest des Dashboards
    
    # --- DASHBOARD ---
    heute = datetime.now().date()
    # WICHTIG: Die nächste Zeile muss exakt unter 'heute' starten (4 Leerzeichen Einrückung)
    df_aktuell_check = df_clean.sort_values(by=[COL_NAME, COL_LETZTER], ascending=[True, False]).drop_duplicates(subset=[COL_NAME])
        
    kritisch = len(df_aktuell_check[df_aktuell_check[COL_NAECHSTER] < heute])
    bald = len(df_aktuell_check[(df_aktuell_check[COL_NAECHSTER] >= heute) & (df_aktuell_check[COL_NAECHSTER] < heute + timedelta(days=30))])

    c1, c2, c3 = st.columns(3)
    if kritisch > 0:
        c1.error(f"⚠️ {kritisch} Sender überfällig!")
    else:
        c1.success("✅ Alle Batterien OK")
            
    if bald > 0:
        c2.warning(f"🔔 {bald} bald fällig")
            
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
                    t = df_clean[df_clean[COL_NAME] == n_in]
                    if not t.empty: b_ort = str(t.iloc[-1][COL_ORT])
                
                o_in = st.text_input("Standort", value=b_ort)
                v_in = st.text_input("Vermerke")
                
                if st.form_submit_button("Speichern"):
                    if n_in:
                        naechster = d_in + timedelta(days=547)
                        new_row = pd.DataFrame([{COL_NAME: n_in, COL_ORT: o_in, COL_LETZTER: d_in, COL_NAECHSTER: naechster, COL_VERMERK: v_in, COL_STATUS: "OK"}])
                        df_to_save = pd.concat([df_raw, new_row], ignore_index=True)
                        conn.update(data=df_to_save)
                        st.cache_data.clear()
                        st.success("Gespeichert!")
                        st.rerun()
                    else:
                        st.error("Name fehlt!")

        # --- ANZEIGE MIT FILTER ---
        st.subheader("📡 Aktueller Status")
        alle_standorte = sorted([s for s in df_clean[COL_ORT].unique() if s != ""])
        filter_ort = st.selectbox("Nach Standort filtern:", ["Alle Standorte"] + alle_standorte)
        
        # NEU: Erst nach Datum (Nächster Wechsel) aufsteigend sortieren, damit Rot oben ist
        # Dann Duplikate entfernen, um den aktuellsten Stand zu behalten
        df_view = df_clean.sort_values(by=[COL_NAECHSTER], ascending=True).drop_duplicates(subset=[COL_NAME])
        
        if filter_ort != "Alle Standorte":
            df_view = df_view[df_view[COL_ORT] == filter_ort]

        st.dataframe(
            df_view.style.apply(style_status, axis=1, heute=heute).format({COL_LETZTER: format_date, COL_NAECHSTER: format_date}),
            use_container_width=True, hide_index=True
        )

        # --- HISTORIE ---
        st.markdown("---")
        with st.expander("🕒 Historie & Verlauf"):
            alle_sender = sorted(df_clean[COL_NAME].unique())
            f_sender = st.selectbox("Sender wählen:", ["Alle"] + alle_sender)
            df_hist = df_clean.sort_values(by=COL_LETZTER, ascending=False).copy()
            if f_sender != "Alle":
                df_hist = df_hist[df_hist[COL_NAME] == f_sender]
            
            df_hist[COL_LETZTER] = df_hist[COL_LETZTER].apply(format_date)
            df_hist[COL_NAECHSTER] = df_hist[COL_NAECHSTER].apply(format_date)
            st.table(df_hist[[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_VERMERK]])

except Exception as e:
    st.error(f"Verbindung zu Google unterbrochen: {e}")
