import streamlit as st
from streamlit_gsheets import GSheetsConnection
import easyocr
import re
import pandas as pd
import cv2
import numpy as np
from datetime import datetime

# --- CONFIGURATION ---
BK_INITIALE = 1000.0

# --- CONNEXION GOOGLE SHEETS ---
# La connexion va lire automatiquement l'URL et les clés dans tes "Secrets"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # On lit l'onglet "Suivi"
        return conn.read(worksheet="Suivi")
    except:
        return pd.DataFrame()

# --- IA OCR ---
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['fr'], gpu=False)

reader = load_ocr()

def extraire_donnees(image_file):
    file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    resultats = reader.readtext(img)
    lignes = [res[1] for res in resultats]
    texte_full = " ".join(lignes).lower()

    # Logique Sport simple
    sport = "Foot"
    if any(m in texte_full for m in ["nba", "basket"]): sport = "Basket"
    elif "tennis" in texte_full: sport = "Tennis"

    # Extraction des nombres (Cote, Mise, Gains)
    nombres = re.findall(r"\d+[\.,]\d+", texte_full)
    nombres_propres = [float(n.replace(',', '.')) for n in nombres]
    
    cote = nombres_propres[0] if len(nombres_propres) > 0 else 1.0
    mise = 0.0
    gains = 0.0

    # Recherche spécifique pour Mise et Gain
    for res in resultats:
        txt = res[1].lower()
        if "mise" in txt:
            m = re.search(r"\d+[\.,]\d+", txt)
            if m: mise = float(m.group().replace(',', '.'))
        if "gain" in txt or "total" in txt:
            v = re.findall(r"\d+[\.,]\d+", txt)
            if v: gains = float(v[-1].replace(',', '.'))

    return {
        "Date": datetime.now().strftime("%d/%m/%Y"),
        "Bookmaker": "Winamax" if "winamax" in texte_full else "Betclic" if "betclic" in texte_full else "Autre",
        "Sport": sport,
        "Intitulé": "Pari IA",
        "Cote": cote,
        "Mise €": mise,
        "Statut": "Gagné" if gains > mise else "Perdu",
        "Net €": round(gains - mise, 2) if gains > 0 else -mise
    }

# --- INTERFACE ---
st.set_page_config(page_title="BetTracker AI", layout="wide")
st.title("📊 BetTracker Cloud AI")

# Chargement des données au démarrage
df_load = load_data()

# --- SIDEBAR : AJOUT ---
st.sidebar.header("📥 Nouveau Ticket")
uploaded_file = st.sidebar.file_uploader("Prendre une photo du ticket", type=['png', 'jpg', 'jpeg'])

if uploaded_file and st.sidebar.button("Analyser & Envoyer au Cloud"):
    with st.spinner('L\'IA analyse votre ticket...'):
        # 1. Extraction
        data = extraire_donnees(uploaded_file)
        new_row = pd.DataFrame([data])
        
        # 2. Mise à jour du DataFrame
        if df_load.empty:
            updated_df = new_row
        else:
            updated_df = pd.concat([df_load, new_row], ignore_index=True)
        
        # 3. Envoi vers Google Sheets (Utilise les secrets)
        conn.update(worksheet="Suivi", data=updated_df)
        
        st.sidebar.success("Ticket enregistré avec succès !")
        st.rerun()

# --- DASHBOARD ---
if not df_load.empty:
    # Métriques
    c1, c2, c3, c4 = st.columns(4)
    benef = df_load['Net €'].sum()
    c1.metric("Paris", len(df_load))
    c2.metric("Bénéfices", f"{benef:.2f} €")
    c3.metric("ROI", f"{(benef/df_load['Mise €'].sum()*100):.1f}%" if df_load['Mise €'].sum()>0 else "0%")
    c4.metric("Bankroll", f"{BK_INITIALE + benef:.2f} €")

    # Tableau
    st.subheader("📋 Historique des paris")
    st.dataframe(df_load.sort_index(ascending=False), hide_index=True, use_container_width=True)
else:
    st.info("Aucune donnée. Importez votre premier ticket via la barre latérale !")
