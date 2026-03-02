import streamlit as st
import pandas as pd
import easyocr
import re
import cv2
import numpy as np
from datetime import datetime

# --- CONFIGURATION ---
SHEET_ID = "12c9Qo55cPvH01k3OiLbiWNR3MBmaBQoRYZY76a9ltkA"
# Lien pour la lecture (Pandas)
URL_READ = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Suivi"
# Lien pour l'écriture (GSheets Connection)
URL_WRITE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
BK_INITIALE = 1000.0

st.set_page_config(page_title="BetTracker AI", layout="wide")

# --- CHARGEMENT IA ---
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['fr'], gpu=False)

reader = load_ocr()

# --- FONCTIONS ---
def load_data():
    try:
        return pd.read_csv(URL_READ)
    except:
        return pd.DataFrame()

def extraire_donnees(image_file):
    file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    resultats = reader.readtext(img)
    lignes = [res[1] for res in resultats]
    texte_full = " ".join(lignes).lower()

    sport = "Foot" if any(m in texte_full for m in ["foot", "ligue"]) else "Basket" if "nba" in texte_full else "Autre"
    
    # Extraction simplifiée des chiffres
    nombres = re.findall(r"\d+[\.,]\d+", texte_full)
    nombres = [float(n.replace(',', '.')) for n in nombres]
    
    cote = nombres[0] if len(nombres) > 0 else 1.50
    mise = nombres[1] if len(nombres) > 1 else 10.0
    gains = nombres[2] if len(nombres) > 2 else 0.0

    return {
        "Date": datetime.now().strftime("%d/%m/%Y"),
        "Bookmaker": "Winamax" if "winamax" in texte_full else "Betclic" if "betclic" in texte_full else "Autre",
        "Sport": sport,
        "Intitulé": "Pari IA",
        "Cote": cote,
        "Mise €": mise,
        "Statut": "Gagné" if gains > 0 else "Perdu",
        "Net €": round(gains - mise, 2) if gains > 0 else -mise
    }

# --- INTERFACE ---
st.title("📊 BetTracker Cloud AI")

df_load = load_data()

# Sidebar
st.sidebar.header("📥 Nouveau Ticket")
uploaded_file = st.sidebar.file_uploader("Capture", type=['png', 'jpg', 'jpeg'])

if uploaded_file and st.sidebar.button("Analyser & Enregistrer"):
    with st.spinner('L\'IA analyse le ticket...'):
        data = extraire_donnees(uploaded_file)
        new_row = pd.DataFrame([data])
        # Note: L'écriture nécessite que les Secrets soient bien configurés
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        updated_df = pd.concat([df_load, new_row], ignore_index=True)
        conn.update(spreadsheet=URL_WRITE, worksheet="Suivi", data=updated_df)
        st.sidebar.success("Ticket ajouté au Cloud !")
        st.rerun()

# Dashboard
if not df_load.empty:
    # Métriques
    c1, c2, c3 = st.columns(3)
    benef = df_load['Net €'].sum()
    c1.metric("Bénéfice Net", f"{benef:.2f} €")
    c2.metric("ROI", f"{(benef/df_load['Mise €'].sum()*100):.1f}%" if df_load['Mise €'].sum()>0 else "0%")
    c3.metric("Bankroll", f"{BK_INITIALE + benef:.2f} €")

    # Tableau
    st.subheader("📋 Historique")
    st.dataframe(df_load, use_container_width=True, hide_index=True)
else:
    st.info("Le fichier est connecté. Ajoutez votre premier ticket !")
