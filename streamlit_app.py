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

# Spaltennamen definieren
COL_NAME = "Name"
COL_ORT = "Standort"
COL_LETZTER = "Letzter Batteriewechsel"
COL_NAECHSTER = "Nächster Wechsel (geplant)"
COL_STATUS = "Status"

# Grundstruktur sicherstellen
if df.empty or COL_NAME not in df.columns:
    df = pd.DataFrame(columns=[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_STATUS])

# Datumsformate bereinigen (für die Berechnung intern)
df[COL_LETZTER] = pd.to_datetime(df[COL_LETZTER], errors='coerce').dt.date
df[COL_NAECHSTER] = pd.to_datetime(df[COL_NAECHSTER], errors='coerce').dt.date

# --- FUNKTION: FARBLOGIK ---
def style_status(row):
    heute = datetime.now().date()
    naechster = row[COL_NAECHSTER]
    if pd.isna(naechster): return [''] * len(row)
    if naechster < heute: return ['background-color: #ffcccc'] * len(row)
    elif naechster < heute + timedelta(days=30): return ['background-color: #fff3cd'] * len(row)
    else: return ['background-color: #d4edda'] * len(row)

# --- EINGABEFORMULAR ---
with st.expander("➕ Neuen Batteriewechsel registrieren", expanded=True):
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        # Eingabe des Namens
        name_input = col1.text_input("Name des Senders (z.B. Z202)").strip()
        
        # Datum per Kalender-Auswahl
        wechsel_datum = col2.date_input("Datum des Wechsels", datetime.now().date(), format="DD.MM.YYYY")
        
        # Standort-Logik: Falls Name bekannt, Standort automatisch suchen
        bekannter_standort = ""
        if name_input and not df.empty:
            treffer = df[df[COL_NAME] == name_input]
            if not treffer.empty:
                bekannter_standort = treffer.iloc[-1][COL_ORT]
        
        # Standort-Feld (nur nötig, wenn neu oder zur Korrektur)
        standort_input = st.text_input("Standort (wird automatisch gemerkt)", value=bekannter_standort)
        
        submit = st.form_submit_button("Wechsel speichern (Avis: 18 Monate)")

        if submit:
            if name_input != "" and standort_input != "":
                naechster_avis = wechsel_datum + timedelta(days=547) # 18 Monate
                
                new_row = pd.DataFrame([{
                    COL_NAME: name_input, 
                    COL_ORT: standort_input, 
                    COL_LETZTER: wechsel_datum, 
                    COL_NAECHSTER: naechster_avis, 
                    COL_STATUS: "OK"
                }])
                
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=df)
                st.success(f"Gespeichert für {name_input}!")
                st.rerun()
            else:
                st.error("Bitte mindestens Name und Standort (beim ersten Mal) angeben!")

# --- ANZEIGE ---
# Hilfsfunktion zur schönen Datumsanzeige (TT.MM.JJJJ)
def format_date(d):
    return d.strftime('%d.%m.%Y') if pd.notnull(d) and hasattr(d, 'strftime') else ""

# Daten für Anzeige aufbereiten
df_display_base = df.dropna(subset=[COL_NAME]).copy()
df_display_base = df_display_base[df_display_base[COL_NAME] != ""]

if not df_display_base.empty:
    st.subheader("📡 Aktueller Batteriestatus")
    
    # Aktuellster Eintrag pro Sender
    df_aktuell = df_display_base.sort_values(by=COL_LETZTER, ascending=False).drop_duplicates(subset=[COL_NAME])
    df_aktuell = df_aktuell.sort_values(by=COL_NAECHSTER, ascending=True)
    
    # Kopie für die formatierte Anzeige
    df_styled = df_aktuell.copy()
    df_styled[COL_LETZTER] = df_styled[COL_LETZTER].apply(format_date)
    df_styled[COL_NAECHSTER] = df_styled[COL_NAECHSTER].apply(format_date)

    st.dataframe(
        df_aktuell.style.apply(style_status, axis=1).format({COL_LETZTER: format_date, COL_NAECHSTER: format_date}),
        use_container_width=True, hide_index=True
    )
    
    st.markdown("---")
    st.subheader("🕒 Historie & Verlauf")
    
    namen_liste = sorted(df_display_base[COL_NAME].astype(str).unique())
    auswahl = st.selectbox("Verlauf für einen Sender anzeigen:", ["Alle anzeigen"] + namen_liste)
    
    if auswahl == "Alle anzeigen":
        df_hist = df_display_base.sort_values(by=COL_LETZTER, ascending=False)
    else:
        df_hist = df_display_base[df_display_base[COL_NAME] == auswahl].sort_values(by=COL_LETZTER, ascending=False)
    
    # Formatierung für die Tabelle
    df_hist_formatted = df_hist.copy()
    df_hist_formatted[COL_LETZTER] = df_hist_formatted[COL_LETZTER].apply(format_date)
    df_hist_formatted[COL_NAECHSTER] = df_hist_formatted[COL_NAECHSTER].apply(format_date)
    
    st.table(df_hist_formatted[[COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER]])
else:
    st.info("Noch keine Daten vorhanden.")
