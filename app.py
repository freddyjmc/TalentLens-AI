"""Punto de entrada de TalentLens AI: `streamlit run app.py`."""

import streamlit as st

from talentlens.ui import applications, assistant, cv, home, interviews, job_search, offers, saved_data
from talentlens.ui.common import get_db

PAGES = {
    "Inicio": home.render,
    "Analizar ofertas": offers.render,
    "Revisar CV": cv.render,
    "Buscar empleo": job_search.render,
    "Mis candidaturas": applications.render,
    "Practicar entrevistas": interviews.render,
    "Datos guardados": saved_data.render,
    "Asistente Inteligente": assistant.render,
}

st.set_page_config(page_title="TalentLens AI", page_icon="🔎")
st.title("TalentLens AI - Tu Asistente de Búsqueda de Empleo")
page = st.sidebar.selectbox("Selecciona una opción", list(PAGES))

try:
    db = get_db()
except ValueError as e:  # falta la configuración de MongoDB en el .env
    st.error(str(e))
    st.stop()

PAGES[page](db)
