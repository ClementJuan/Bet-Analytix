import streamlit as st
import pandas as pd

st.title("📊 BetTracker Cloud (Méthode Directe)")

# 1. On transforme ton URL en lien de téléchargement direct
SHEET_ID = "12c9Qo55cPvH01k3OiLbiWNR3MBmaBQoRYZY76a9ltkA"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Suivi"

def load_data():
    try:
        # On lit directement le CSV via Pandas
        return pd.read_csv(URL_CSV)
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        return pd.DataFrame()

df_load = load_data()

if not df_load.empty:
    st.success("Connexion réussie !")
    st.dataframe(df_load, hide_index=True)
else:
    st.info("La feuille est vide ou inaccessible. Vérifiez qu'il y a du texte en A1.")
