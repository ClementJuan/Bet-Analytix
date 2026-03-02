import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.title("Test Connexion Google Sheets")

# URL directe pour forcer le test
URL_TEST = "https://docs.google.com/spreadsheets/d/12c9Qo55cPvH01k3OiLbiWNR3MBmaBQoRYZY76a9ltkA/edit"

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # On force l'URL ici pour voir si ça débloque
    df = conn.read(spreadsheet=URL_TEST, worksheet="Suivi")
    st.success("Connexion réussie !")
    st.write(df)
except Exception as e:
    st.error(f"Erreur de connexion : {e}")
