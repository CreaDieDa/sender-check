import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Sender-Wartung", page_icon="🔋")

st.title("🔋 Sender-Batterie-Check")
st.write("Trage hier den Batteriewechsel für einen Sender ein:")

# 1. Verbindung zur Tabelle herstellen
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Bestehende Daten einlesen
df = conn.read()

# 3. Das Eingabeformular
with st.form("wartungs_form"):
    sender_name = st.text_input("Name des Senders")
    standort = st.text_input("Standort / Position")
    datum = st.date_input("Datum des Wechsels")
    bemerkung = st.text_area("Bemerkungen (optional)")
    
    submit_button = st.form_submit_button(label="In Tabelle speichern")

if submit_button:
    if sender_name == "" or standort == "":
        st.error("Bitte mindestens Name und Standort ausfüllen!")
    else:
        # Neue Zeile als Datenrahmen (DataFrame) erstellen
        new_row = pd.DataFrame([{
            "Sender Name": sender_name,
            "Standort": standort,
            "Letzter Batteriewechsel": str(datum),
            "Nächster Wechsel (geplant)": bemerkung # Hier kannst du später eine Formel nutzen
        }])
        
        # Die neuen Daten an die alten Daten anhängen
        updated_df = pd.concat([df, new_row], ignore_index=True)
        
        # Zurück in die Google Tabelle schreiben
        conn.update(data=updated_df)
        
        st.success(f"Erfolgreich gespeichert: {sender_name} am {datum}")
        st.balloons() # Ein kleiner Feiereffekt

# 4. Vorschau der Tabelle mit Farblogik
st.subheader("Aktuelle Liste (Wartungsstatus):")

def highlight_status(row):
    # Hier definieren wir die Farben
    # Beispiel: Wenn in der Spalte "Standort" das Wort "WICHTIG" steht, wird es gelb
    if "WICHTIG" in str(row["Standort"]).upper():
        return ['background-color: #ffffcc'] * len(row)
    return [''] * len(row)

# Die Tabelle mit Styling anzeigen
st.dataframe(df.style.apply(highlight_status, axis=1))
