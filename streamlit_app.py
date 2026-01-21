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

# Definieren der Spaltennamen (Exakt wie in deiner Tabelle)
COL_NAME = "Name"
COL_ORT = "Standort"
COL_LETZTER = "Letzter Batteriewechsel"
COL_NAECHSTER = "Nächster Wechsel (geplant)"
COL_STATUS = "Status"

# Struktur prüfen/erstellen falls Tabelle leer ist
if df.empty:
    df = pd.DataFrame(columns=[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_STATUS])

# Datumsformate bereinigen (verhindert den TypeError bei leeren Zellen)
df[COL_LETZTER] = pd.to_datetime(df[COL_LETZTER], errors='coerce').dt.date
df[COL_NAECHSTER] = pd.to_datetime(df[COL_NAECHSTER], errors='coerce').dt.date

# --- FUNKTION: FARBLOGIK ---
def style_status(row):
    heute = datetime.now().date()
    naechster = row[COL_NAECHSTER]
    
    # Falls kein Datum vorhanden ist (NaT), Zeile neutral lassen
    if pd.isna(naechster) or not isinstance(naechster, (datetime, pd.Timestamp, type(heute))):
        return [''] * len(row)
    
    if naechster < heute:
        return ['background-color: #ffcccc'] * len(row) # Rot: Überfällig
    elif naechster < heute + timedelta(days=30):
        return ['background-color: #fff3cd'] * len(row) # Gelb: < 30 Tage
    else:
        return ['background-color: #d4edda'] * len(row) # Grün: OK

# --- EINGABEFORMULAR ---
with st.expander("➕ Neuen Wechsel registrieren", expanded=True):
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name_input = col1.text_input("Name des Senders")
        standort_input = col2.text_input("Standort")
        submit = st.form_submit_button("Speichern (Avis: 18 Monate)")

        if submit and name_input and standort_input:
            heute = datetime.now().date()
            naechster_avis = heute + timedelta(days=547) # 18 Monate
            
            new_row = pd.DataFrame([{
                COL_NAME: name_input, 
                COL_ORT: standort_input, 
                COL_LETZTER: heute, 
                COL_NAECHSTER: naechster_avis, 
                COL_STATUS: "OK"
            }])
            
            df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=df)
            st.success("Erfolgreich gespeichert!")
            st.rerun()

# --- TABELLE ANZEIGEN ---
st.subheader("Übersicht")
if not df.empty:
    # Sortieren: Die dringendsten oben, leere Daten ganz nach unten
    df_display = df.sort_values(by=COL_NAECHSTER, ascending=True, na_position='last')
    
    st.dataframe(
        df_display.style.apply(style_status, axis=1),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Noch keine Daten vorhanden. Bitte ersten Wechsel oben eintragen.")

# --- RESET FUNKTION ---
with st.expander("⚙️ Einstellungen"):
    if st.button("Tabelle leeren (Reset)"):
        empty_df = pd.DataFrame(columns=[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_STATUS])
        conn.update(data=empty_df)
        st.warning("Tabelle wurde geleert.")
        st.rerun()
