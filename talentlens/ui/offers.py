"""Página «Analizar ofertas»."""

import streamlit as st

from talentlens.db import JOB_OFFERS, DBManager
from talentlens.offers.analysis import analyze_job_offer
from talentlens.offers.scraper import fetch_offer
from talentlens.ui.common import file_key, read_uploaded, save


def render(db: DBManager) -> None:
    st.header("Análisis de Ofertas de Empleo")
    option = st.radio("Selecciona el método para analizar la oferta:", ["Pegar un enlace", "Subir un archivo"])

    if option == "Pegar un enlace":
        url = st.text_input("Pega el enlace a la oferta de empleo")
        current_source = url
        if url and st.button("Analizar oferta"):
            try:
                with st.spinner("Leyendo y analizando la oferta..."):
                    title, page_text = fetch_offer(url)
                    analysis = analyze_job_offer(page_text)
                st.session_state["offer_result"] = {
                    "source": url,
                    "data": {"url": url, "title": title, "text": page_text, "analysis": analysis},
                }
            except Exception as e:
                st.error(f"Error al analizar la oferta: {e}")
    else:
        uploaded = st.file_uploader("Sube una oferta de empleo (texto, PDF o Word)", type=["txt", "pdf", "docx"])
        current_source = file_key(uploaded) if uploaded else None
        result = st.session_state.get("offer_result")
        # Analizar solo cuando cambia el archivo, no en cada recarga de la página
        if uploaded and (not result or result["source"] != current_source):
            try:
                offer_text = read_uploaded(uploaded)
                with st.spinner("Analizando la oferta..."):
                    analysis = analyze_job_offer(offer_text)
                st.session_state["offer_result"] = {
                    "source": current_source,
                    "data": {"text": offer_text, "analysis": analysis},
                }
            except Exception as e:
                st.error(f"Error al analizar la oferta: {e}")

    # Mostrar y guardar el último análisis (se conserva entre recargas)
    result = st.session_state.get("offer_result")
    if result and result["source"] == current_source:
        st.subheader("Análisis de la oferta:")
        if "title" in result["data"]:
            st.write(f"**Título del empleo:** {result['data']['title']}")
        st.write(result["data"]["analysis"])

        if st.button("Guardar análisis"):
            save(db, JOB_OFFERS, dict(result["data"]), "Oferta guardada en la base de datos")
