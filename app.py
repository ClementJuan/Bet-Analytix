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
# On définit l'URL une seule fois ici pour tout le script
URL_SHEET = "https://docs.google.com/spreadsheets/d/12c9Qo55cPvH01k3OiLbiWNR3MBmaBQoRYZY76a9ltkA/edit"

# --- CONNEXION GOOGLE SHEETS ---
# Utilise les identifiants JSON stockés dans Streamlit Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Lecture de l'onglet "Suivi" via la connexion sécurisée
        return conn.read(spreadsheet=URL_SHEET, worksheet="Suivi")
    except Exception as e:
        # Si la feuille est vide ou inaccessible, on retourne un tableau vide
        return pd.DataFrame()

# --- IA OCR (Mise en cache pour la rapidité) ---
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['fr'], gpu=False)

reader = load_ocr()

def extraire_donnees(image_file):
    # Conversion de l'image pour OpenCV et EasyOCR
    file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    resultats = reader.readtext(img)
    lignes = [res[1] for res in resultats]
    texte_full = " ".join(lignes).lower()

    # Détection simplifiée du sport
    sport = "Foot"
    if any(m in texte_full for m in ["nba", "basket"]): sport = "Basket"
    elif "tennis" in texte_full: sport = "Tennis"

    # Extraction des nombres (Cote, Mise, Gains)
    nombres = re.findall(r"\d+[\.,]\d+", texte_full)
    nombres_propres = [float(n.
