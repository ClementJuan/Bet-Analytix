import streamlit as st
from streamlit_gsheets import GSheetsConnection
import easyocr
import re
import pandas as pd
import cv2
import numpy as np
from datetime import datetime

# --- CONFIGURATION ---
# Remplace par l'URL de ta Google Sheet (Partager -> Copier le lien)
URL_SHEET = "TON_URL_GOOGLE_SHEET_ICI"
BK_INITIALE = 1000.0

# --- CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(spreadsheet=URL_SHEET, worksheet="Suivi")

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

    # Logique Sport
    sport = "Autre"
    if any(m in texte_full for m in ["foot", "score", "match"]): sport = "Foot"
    elif any(m in texte_full for m in ["nba", "basket"]): sport = "Basket"

    # Date
    date_pari = datetime.now().strftime("%d/%m/%Y")
    for lig in reversed(lignes):
        if any(m in lig.lower() for m in ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']):
            date_pari = lig
            break

    # Chiffres
    nombres = re.findall(r"\d+[\.,]\d+", texte_full)
    nombres_propres = [float(n.replace(',', '.')) for n in nombres]
    cote = nombres_propres[0] if nombres_propres else 1.0
    
    mise = 0.0
    for res in resultats:
        if "mise" in res[1].lower():
            m = re.search(r"\d+[\.,]\d+", res[1])
            if m: mise = float(m.group().replace(',', '.'))
            
    gains = 0.0
    for res in resultats:
        if "gain" in res[1].lower():
            v = re.findall(r"\d+[\.,]\d+", res[1])
            if v: gains = float(v[0].replace(',', '.'))

    return {
        "Date": date_pari,
        "Bookmaker": "Winamax" if "winamax" in texte_full else "Autre",
        "Sport": sport,
        "Intitulé": "Nouveau Pari",
        "Cote": cote,
        "Mise €": mise,
        "Statut": "Gagné" if gains > 0 else "Perdu",
        "Net €": round(gains - mise, 2)
    }

# --- INTERFACE ---
st.set_page_config(page_title="BetTracker Cloud", layout="wide")
st.title("☁️ BetTracker Cloud (IA + GSheets)")

# On charge les données existantes
try:
    df_load = load_data()
except:
    st.error("Impossible de lire la Google Sheet. Vérifiez l'URL et les accès.")
    df_load = pd.DataFrame()

# --- SIDEBAR : AJOUT ---
st.sidebar.header("📥 Nouveau Ticket")
uploaded_file = st.sidebar.file_uploader("Capture", type=['png', 'jpg', 'jpeg'])

if uploaded_file and st.sidebar.button("Analyser & Envoyer au Cloud"):
    with st.spinner('Analyse...'):
        data = extraire_donnees(uploaded_file)
        new_row = pd.DataFrame([data])
        updated_df = pd.concat([df_load, new_row], ignore_index=True)
        conn.update(spreadsheet=URL_SHEET, worksheet="Suivi", data=updated_df)
        st.sidebar.success("Données envoyées sur Google Sheets !")
        st.rerun()

# --- SIDEBAR : SUPPRESSION ---
st.sidebar.markdown("---")
if not df_load.empty:
    st.sidebar.header("🗑️ Gestion")
    delete_options = [f"Ligne {i} : {df_load.loc[i, 'Date']} ({df_load.loc[i, 'Net €']}€)" for i in df_load.index]
    to_delete = st.sidebar.selectbox("Supprimer un pari", options=delete_options)
    
    if st.sidebar.button("❌ Confirmer suppression"):
        idx = int(to_delete.split(" : ")[0].split(" ")[1])
        df_load = df_load.drop(idx)
        conn.update(spreadsheet=URL_SHEET, worksheet="Suivi", data=df_load)
        st.sidebar.warning("Pari supprimé du Cloud.")
        st.rerun()

# --- DASHBOARD ---
if not df_load.empty:
    # Filtres
    st.sidebar.markdown("---")
    f_sport = st.sidebar.multiselect("Sport", df_load["Sport"].unique(), default=df_load["Sport"].unique())
    df_filtered = df_load[df_load["Sport"].isin(f_sport)].reset_index(drop=True)

    # Métriques
    c1, c2, c3, c4 = st.columns(4)
    benef = df_filtered['Net €'].sum()
    c1.metric("Paris", len(df_filtered))
    c2.metric("Bénéfices", f"{benef:.2f} €")
    c3.metric("ROI", f"{(benef/df_filtered['Mise €'].sum()*100):.1f}%" if df_filtered['Mise €'].sum()>0 else "0%")
    c4.metric("Bankroll", f"{BK_INITIALE + benef:.2f} €")

    # Graphique
    st.subheader("📈 Évolution")
    df_filtered['Evo'] = BK_INITIALE + df_filtered['Net €'].cumsum()
    st.line_chart(df_filtered['Evo'])

    # Tableau
    st.subheader("📋 Historique Cloud")
    st.dataframe(df_filtered.sort_index(ascending=False), hide_index=True, use_container_width=True)
else:
    st.info("Aucune donnée détectée sur la Google Sheet.")