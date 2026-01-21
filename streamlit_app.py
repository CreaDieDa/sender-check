import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Seite konfigurieren
st.set_page_config(page_title="Sender-Batterie-Check", page_icon="🔋")

st.title("🔋 Sender-Batterie-Check")

# 1. Verbindung zur Google Tabelle
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Daten einlesen & Spaltennamen fixieren
df = conn.read()

# Falls die Tabelle komplett leer ist, Grundstruktur erstellen
if df.empty or 'Nächster Wechsel' not in df.columns:
    df = pd.DataFrame(columns=["Name", "Standort", "Letzter Batteriewechsel", "Nächster Wechsel", "Status"])

# Datumsformate bereinigen (verhindert den TypeError)
df['Letzter Batteriewechsel'] = pd.to_datetime(df['Letzter Batteriewechsel'], errors='coerce').dt.date
df['Nächster Wechsel'] = pd.to_datetime(df['Nächster Wechsel'], errors='coerce').dt.date

# --- FUNKTION: FARBLOGIK ---
def style_status(row):
    heute = datetime.now().date()
    naechster = row['Nächster Wechsel']
    
    # Schutz vor leeren Datumsfeldern
    if pd.isna(naechster):
        return [''] * len(row)
    
    if naechster < heute:
        return ['background-color: #ffcccc'] * len(row) # Rot
    elif naechster < heute + timedelta(days=30):
        return ['background-color: #fff3cd'] * len(row) # Gelb
    else:
        return ['background-color: #d4edda'] * len(row) # Grün

# --- EINGABE ---
with st.expander("➕ Neuen Wechsel registrieren", expanded=True):
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("Name des Senders")
        standort = col2.text_input("Standort")
        submit = st.form_submit_button("Speichern (Avis: 18 Monate)")

        if submit and name and standort:
            heute = datetime.now().date()
            naechster = heute + timedelta(days=547) # 18 Monate
            
            new_row = pd.DataFrame([{
                "Name": name, "Standort": standort, 
                "Letzter Batteriewechsel": heute, 
                "Nächster Wechsel": naechster, "Status": "OK"
            }])
            
            df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=df)
            st.success("Gespeichert!")
            st.rerun()

# --- TABELLE ANZEIGEN ---
st.subheader("Übersicht")
if not df.empty:
    # Sortieren (Kritische oben), leere Daten nach unten
    df_display = df.sort_values(by="Nächster Wechsel", ascending=True, na_position='last')
    
    st.dataframe(
        df_display.style.apply(style_status, axis=1),
        use_container_width=True,
        hide_index=True
    )
else:
    st.write("Noch keine Daten vorhanden. Nutze das Formular oben!")

# --- ADMIN BEREICH ---
with st.expander("⚙️ Einstellungen"):
    if st.button("Tabelle komplett leeren (Reset)"):
        empty_df = pd.DataFrame(columns=["Name", "Standort", "Letzter Batteriewechsel", "Nächster Wechsel", "Status"])
        conn.update(data=empty_df)
        st.warning("Alle Daten wurden gelöscht.")
        st.rerun()
