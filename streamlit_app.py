import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Seite konfigurieren
st.set_page_config(page_title="Sender-Batterie-Check", page_icon="🔋")

st.title("🔋 Sender-Batterie-Check")

# 1. Verbindung zur Google Tabelle
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Daten einlesen
df = conn.read()

# --- EXAKTE SPALTEN-DEFINITIONEN ---
COL_NAME = "Sender Name"
COL_ORT = "Standort"
COL_LETZTER = "Letzter Batteriewechsel"
COL_NAECHSTER = "Nächster Wechsel (geplant)"
COL_VERMERK = "Vermerke (z.B. Batterie)"
COL_STATUS = "Status"

# Grundstruktur sicherstellen
if df.empty or COL_NAME not in df.columns:
    df = pd.DataFrame(columns=[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_VERMERK, COL_STATUS])

# Datumsformate bereinigen (verhindert Abstürze bei leeren Feldern)
df[COL_LETZTER] = pd.to_datetime(df[COL_LETZTER], errors='coerce').dt.date
df[COL_NAECHSTER] = pd.to_datetime(df[COL_NAECHSTER], errors='coerce').dt.date

# --- FUNKTION: FARBLOGIK ---
def style_status(row):
    heute = datetime.now().date()
    naechster = row[COL_NAECHSTER]
    if pd.isna(naechster) or not hasattr(naechster, 'year'): return [''] * len(row)
    if naechster < heute: return ['background-color: #ffcccc'] * len(row) # Rot
    elif naechster < heute + timedelta(days=30): return ['background-color: #fff3cd'] * len(row) # Gelb
    else: return ['background-color: #d4edda'] * len(row) # Grün

# --- EINGABEFORMULAR ---
with st.expander("➕ Neuen Batteriewechsel registrieren", expanded=True):
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        name_input = col1.text_input("Sender Name (z.B. Z202)").strip()
        wechsel_datum = col2.date_input("Datum des Wechsels", datetime.now().date(), format="DD.MM.YYYY")
        
        # Automatischer Standort-Finder
        bekannter_standort = ""
        if name_input and not df.empty:
            valid_names = df.dropna(subset=[COL_NAME])
            treffer = valid_names[valid_names[COL_NAME].astype(str) == name_input]
            if not treffer.empty:
                bekannter_standort = str(treffer.iloc[-1][COL_ORT])
        
        standort_input = st.text_input("Standort", value=bekannter_standort)
        vermerk_input = st.text_input("Vermerke (z.B. Batteriebezeichnung)")
        
        submit = st.form_submit_button("Wechsel speichern")

        if submit:
            if name_input != "":
                naechster_avis = wechsel_datum + timedelta(days=547) # 18 Monate
                
                new_row = pd.DataFrame([{
                    COL_NAME: name_input, 
                    COL_ORT: standort_input, 
                    COL_LETZTER: wechsel_datum, 
                    COL_NAECHSTER: naechster_avis,
                    COL_VERMERK: vermerk_input,
                    COL_STATUS: "OK"
                }])
                
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=df)
                st.success(f"Eintrag für {name_input} gespeichert!")
                st.rerun()
            else:
                st.error("Bitte einen Sendernamen eingeben!")

# --- ANZEIGE ---
def format_date(d):
    return d.strftime('%d.%m.%Y') if pd.notnull(d) and hasattr(d, 'strftime') else ""

# Nur Zeilen mit echtem Namen filtern (entfernt die "None" Zeilen aus deinem Bild)
df_clean = df.dropna(subset=[COL_NAME]).copy()
df_clean = df_clean[df_clean[COL_NAME].astype(str).str.strip() != ""]

if not df_clean.empty:
    st.subheader("📡 Aktueller Batteriestatus")
    df_aktuell = df_clean.sort_values(by=COL_LETZTER, ascending=False).drop_duplicates(subset=[COL_NAME])
    df_aktuell = df_aktuell.sort_values(by=COL_NAECHSTER, ascending=True)
    
    st.dataframe(
        df_aktuell.style.apply(style_status, axis=1).format({COL_LETZTER: format_date, COL_NAECHSTER: format_date}),
        use_container_width=True, hide_index=True
    )
    
    st.markdown("---")
    st.subheader("🕒 Historie & Verlauf")
    
    namen_liste = sorted(df_clean[COL_NAME].astype(str).unique())
    auswahl = st.selectbox("Sender auswählen:", ["Alle anzeigen"] + namen_liste)
    
    df_hist = df_clean if auswahl == "Alle anzeigen" else df_clean[df_clean[COL_NAME].astype(str) == auswahl]
    df_hist = df_hist.sort_values(by=COL_LETZTER, ascending=False)
    
    # Anzeigeformatierung
    df_view = df_hist.copy()
    df_view[COL_LETZTER] = df_view[COL_LETZTER].apply(format_date)
    df_view[COL_NAECHSTER] = df_view[COL_NAECHSTER].apply(format_date)
    
    st.table(df_view[[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_VERMERK]])
else:
    st.info("Noch keine Daten vorhanden.")
