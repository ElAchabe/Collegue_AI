import streamlit as st


import theme
theme.inject_theme()
theme.render_sidebar()


st.title("Paramètres")

st.write("API locale: http://127.0.0.1:8000")
st.write("Interface Streamlit: http://127.0.0.1:8501")
st.write("Données propres: data/reference/")
st.write("Plans générés: data/plans/")

st.warning("L'assistant IA est optionnel. Il doit être désactivé par défaut dans ce prototype.")
