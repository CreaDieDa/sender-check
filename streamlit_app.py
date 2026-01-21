import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# Seite konfigurieren
st.set_page_config(page_title="Sender-Batterie-Check", page_icon="🔋")

st.title("🔋 Sender-Batterie-Check")
st.markdown("Verwalte und überwache die Batteriewechsel deiner ABUS-Sender.")

# 1. Verbindung zur Google Tabelle herstellen
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Daten einlesen
df = conn.read()

# Hilfsfunktion: Datumsspalten umwandeln, falls sie als Text kommen
df['Letzter Batteriewechsel'] = pd.to_datetime(df['Letzter Batteriewechsel']).dt.date
df['Nächster Wechsel'] = pd.to_datetime(df['Nächster Wechsel']).dt.date

# --- FUNKTION: FARBLOGIK (Ampelsystem) ---
def style_status(row):
    heute = datetime.now().date()
    naechster = row['Nächster Wechsel']
    
    # Rot: Überfällig
    if naechster < heute:
        return ['background-color: #ffcccc'] * len(row)
    # Gelb: Fällig in den nächsten 30 Tagen
    elif naechster < heute + timedelta(days=30):
        return ['background-color: #fff3cd'] * len(row)
    # Grün: Alles okay
    else:
        return ['background-color: #d4edda'] * len(row)

# --- EINGABEFORMULAR ---
st.subheader("Neuen Wechsel registrieren")
with st.form("entry_form"):
    name = st.text_input("Name des Senders (z.B. Sender 01)")
    standort = st.text_input("Standort (z.B. Kellerfenster)")
    
    submit_button = st.form_submit_button("Wechsel jetzt speichern")

    if submit_button:
        if name and standort:
            # Automatische Berechnung
            heute = datetime.now().date()
            # 18 Monate = ca. 547 Tage
            naechster_termin = heute + timedelta(days=547)
            
            # Neue Datenzeile erstellen
            new_data = pd.DataFrame([{
                "Name": name,
                "Standort": standort,
                "Letzter Batteriewechsel": heute,
                "Nächster Wechsel": naechster_termin,
                "Status": "OK"
            }])
            
            # Daten an bestehende Tabelle anhängen
            updated_df = pd.concat([df, new_data], ignore_index=True)
            
            # In Google Sheets speichern
            conn.update(data=updated_df)
            st.success(f"Erfolgreich gespeichert! Nächster Wechsel am {naechster_termin.strftime('%d.%m.%Y')}")
            st.balloons()
            # Seite neu laden, um Tabelle zu aktualisieren
            st.rerun()
        else:
            st.warning("Bitte fülle Name und Standort aus.")

# --- ANZEIGE DER LISTE ---
st.subheader("Status-Übersicht")

# Sortierung: Die kritischen (frühesten Termine) zuerst
df_sorted = df.sort_values(by="Nächster Wechsel", ascending=True)

# Tabelle mit Farben anzeigen
st.dataframe(
    df_sorted.style.apply(style_status, axis=1),
    use_container_width=True,
    hide_index=True
)

st.info("💡 Rot = Überfällig | Gelb = Bald fällig (< 30 Tage) | Grün = OK")
