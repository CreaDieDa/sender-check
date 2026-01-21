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

# --- SPALTEN-DEFINITIONEN ---
COL_NAME = "Sender Name"
COL_ORT = "Standort"
COL_LETZTER = "Letzter Batteriewechsel"
COL_NAECHSTER = "Nächster Wechsel (geplant)"
COL_VERMERK = "Vermerke (z.B. Batterie)"
COL_STATUS = "Status"

# Liste aller benötigten Spalten
ALL_COLUMNS = [COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_VERMERK, COL_STATUS]

# Struktur sicherstellen: Falls Spalten fehlen, leeren DataFrame mit korrekten Spalten erstellen
if df is None or df.empty or COL_NAME not in df.columns:
    df = pd.DataFrame(columns=ALL_COLUMNS)

# Sicherstellen, dass alle Spalten existieren (verhindert KeyError)
for col in ALL_COLUMNS:
    if col not in df.columns:
        df[col] = None

# Datumsformate bereinigen
df[COL_LETZTER] = pd.to_datetime(df[COL_LETZTER], errors='coerce').dt.date
df[COL_NAECHSTER] = pd.to_datetime(df[COL_NAECHSTER], errors='coerce').dt.date

# --- FUNKTION: FARBLOGIK ---
def style_status(row):
    heute = datetime.now().date()
    naechster = row[COL_NAECHSTER]
    if pd.isna(naechster) or not hasattr(naechster, 'year'): return [''] * len(row)
    if naechster < heute: return ['background-color: #ffcccc'] * len(row)
    elif naechster < heute + timedelta(days=30): return ['background-color: #fff3cd'] * len(row)
    else: return ['background-color: #d4edda'] * len(row)

# --- EINGABEFORMULAR ---
with st.expander("➕ Neuen Batteriewechsel registrieren", expanded=True):
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        name_input = col1.text_input("Sender Name (z.B. Z202)").strip()
        # Kalender Auswahl
        wechsel_datum = col2.date_input("Datum des Wechsels", datetime.now().date(), format="DD.MM.YYYY")
        
        # Standort automatisch finden
        bekannter_standort = ""
        if name_input and not df.empty:
            valid_names = df.dropna(subset=[COL_NAME])
            treffer = valid_names[valid_names[COL_NAME].astype(str) == name_input]
            if not treffer.empty:
                bekannter_standort = str(treffer.iloc[-1][COL_ORT])
        
        standort_input = st.text_input("Standort", value=bekannter_standort)
        vermerk_input = st.text_input("Vermerke (z.B. CR2032)")
        
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
                
                # Daten anhängen und speichern
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=df)
                st.success(f"Eintrag für {name_input} gespeichert!")
                st.rerun()
            else:
                st.error("Bitte einen Namen eingeben!")

# --- ANZEIGE ---
def format_date(d):
    return d.strftime('%d.%m.%Y') if pd.notnull(d) and hasattr(d, 'strftime') else ""

# Filtert ungültige Zeilen ("None" Einträge) komplett aus
df_clean = df.dropna(subset=[COL_NAME]).copy()
df_clean = df_clean[df_clean[COL_NAME].astype(str).str.lower() != "none"]

if not df_clean.empty:
    st.subheader("📡 Aktueller Batteriestatus")
    # Nur aktuellsten Eintrag pro Sender
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
    
    # Tabelle für Historie vorbereiten (nur Spalten nehmen, die wirklich da sind)
    avail_cols = [c for c in [COL_NAME, COL_ORT, COL_LETZTER, COL_NAECHSTER, COL_VERMERK] if c in df_hist.columns]
    df_view = df_hist[avail_cols].copy()
    
    if COL_LETZTER in df_view.columns: df_view[COL_LETZTER] = df_view[COL_LETZTER].apply(format_date)
    if COL_NAECHSTER in df_view.columns: df_view[COL_NAECHSTER] = df_view[COL_NAECHSTER].apply(format_date)
    
    st.table(df_view)
else:
    st.info("Noch keine Daten vorhanden. Nutze das Formular oben!")
