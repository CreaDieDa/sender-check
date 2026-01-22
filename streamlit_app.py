import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 1. SEITENKONFIGURATION
st.set_page_config(page_title="ABUS Batteriecheck", page_icon="🔋", layout="wide")

# CSS für Vollbild-Modus
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

# Hilfsfunktionen
def format_date(d):
    return d.strftime('%d.%m.%Y') if pd.notnull(d) and hasattr(d, 'strftime') else ""

def style_status(row, heute):
    n = row["Nächster Wechsel (geplant)"]
    if pd.isna(n) or n == "": return [''] * len(row)
    if n < heute: # Überfällig
        return ['background-color: #ffcccc; color: black; font-weight: bold'] * len(row)
    elif n < heute + timedelta(days=30): # Bald fällig
        return ['background-color: #fff3cd; color: black; font-weight: bold'] * len(row)
    else: # OK
        return ['background-color: #d4edda; color: black'] * len(row)

try:
    # 1. Daten laden
    df_raw = load_data()
    df = df_raw.copy()
    heute = datetime.now().date()

    # Spaltennamen definieren
    COL_NAME = "Sender Name"
    COL_ORT = "Standort"
    COL_LETZTER = "Letzter Batteriewechsel"
    COL_NAECHSTER = "Nächster Wechsel (geplant)"
    COL_VERMERK = "Vermerke (z.B. Batterie)"

    # 2. DATUMS-KONVERTIERUNG
    df[COL_LETZTER] = pd.to_datetime(df[COL_LETZTER], errors='coerce').dt.date
    df[COL_NAECHSTER] = pd.to_datetime(df[COL_NAECHSTER], errors='coerce').dt.date
    
    # 3. AUTOMATISCHE ERGÄNZUNG (+547 Tage)
    maske = (df[COL_LETZTER].notnull()) & (df[COL_NAECHSTER].isnull())
    df.loc[maske, COL_NAECHSTER] = df.loc[maske, COL_LETZTER] + timedelta(days=547)

    # REINIGUNG DER TEXT-SPALTEN
    for col in [COL_ORT, COL_VERMERK, "Status"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).replace(["None", "nan", "NaN", "<NA>"], "")

    # 4. SÄUBERUNG & SORTIERUNG
    df_clean = df[df[COL_NAME].notnull() & (df[COL_NAME] != "")].copy()
    
    # Neueste zuerst (für die Auswahl des aktuellen Stands)
    df_aktuell = df_clean.sort_values(by=[COL_NAME, COL_LETZTER], ascending=[True, False])
    df_aktuell = df_aktuell.drop_duplicates(subset=[COL_NAME], keep='first')

    # --- AUTOMATISCHER STATUS-TEXT ---
    df_aktuell["Status"] = df_aktuell[COL_NAECHSTER].apply(
        lambda x: "⚠️ ÜBERFÄLLIG" if x < heute else ("🔔 BALD FÄLLIG" if x < heute + timedelta(days=30) else "✅ OK")
    )
    
    # Finaler View: Rot (Überfällig) nach oben
    df_view_final = df_aktuell.sort_values(by=[COL_NAECHSTER], ascending=True)

    # --- DASHBOARD ---
    kritisch = len(df_view_final[df_view_final[COL_NAECHSTER] < heute])
    bald = len(df_view_final[(df_view_final[COL_NAECHSTER] >= heute) & (df_view_final[COL_NAECHSTER] < heute + timedelta(days=30))])

    c1, c2, c3 = st.columns(3)
    if kritisch > 0:
        c1.error(f"⚠️ {kritisch} Sender überfällig!")
    else:
        c1.success("✅ Alle Batterien OK")
            
    if bald > 0:
        c2.warning(f"🔔 {bald} bald fällig")
            
    c3.metric("Sender gesamt", len(df_view_final))

    st.markdown("---")

    # --- EINGABE ---
    with st.expander("➕ Neuen Batteriewechsel registrieren"):
        with st.form("entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            n_in = col1.text_input("Sender Name (z.B. Z202)").strip()
            d_in = col2.date_input("Wechseldatum", heute, format="DD.MM.YYYY")
            
            b_ort = ""
            if n_in and not df_aktuell.empty:
                t = df_aktuell[df_aktuell[COL_NAME] == n_in]
                if not t.empty: b_ort = str(t.iloc[0][COL_ORT])
            
            o_in = st.text_input("Standort", value=b_ort)
            v_in = st.text_input("Vermerke")
            
            if st.form_submit_button("Speichern"):
                if n_in:
                    naechster = d_in + timedelta(days=547)
                    new_row = pd.DataFrame([{COL_NAME: n_in, COL_ORT: o_in, COL_LETZTER: d_in, COL_NAECHSTER: naechster, COL_VERMERK: v_in}])
                    df_to_save = pd.concat([df_raw, new_row], ignore_index=True)
                    conn.update(data=df_to_save)
                    st.cache_data.clear()
                    st.success("Gespeichert!")
                    st.rerun()
                else:
                    st.error("Name fehlt!")

    # --- ANZEIGE MIT FILTER ---
    st.subheader("📡 Aktueller Status (Überfällig oben)")
    
    alle_standorte = sorted([s for s in df_aktuell[COL_ORT].unique() if s != ""])
    filter_ort = st.selectbox("Nach Standort filtern:", ["Alle Standorte"] + alle_standorte)
    
    df_display = df_view_final.copy()
    if filter_ort != "Alle Standorte":
        df_display = df_display[df_display[COL_ORT] == filter_ort]

    # Hier wird die Tabelle angezeigt
    st.dataframe(
        df_display.style.apply(style_status, axis=1, heute=heute).format({
            COL_LETZTER: format_date, 
            COL_NAECHSTER: format_date
        }),
        use_container_width=True, 
        hide_index=True,
        column_order=(COL_NAME, "Status", COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_VERMERK)
    )

    # --- HISTORIE ---
    st.markdown("---")
    with st.expander("🕒 Historie & Verlauf (Alle Einträge)"):
        alle_sender = sorted(df_clean[COL_NAME].unique())
        f_sender = st.selectbox("Sender wählen:", ["Alle"] + alle_sender)
        df_hist = df_clean.sort_values(by=COL_LETZTER, ascending=False).copy()
        
        if f_sender != "Alle":
            df_hist = df_hist[df_hist[COL_NAME] == f_sender]
        
        df_hist[COL_LETZTER] = df_hist[COL_LETZTER].apply(format_date)
        df_hist[COL_NAECHSTER] = df_hist[COL_NAECHSTER].apply(format_date)
        st.table(df_hist[[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_VERMERK]])

except Exception as e:
    st.error(f"Fehler: {e}")
