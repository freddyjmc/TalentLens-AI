"""Página «Practicar entrevistas»."""

import streamlit as st

from talentlens.assistant import interview_questions
from talentlens.db import DBManager


def render(db: DBManager) -> None:
    st.header("Práctica de Entrevistas")
    role = st.text_input("Ingresa el rol para el que deseas practicar")
    if role and st.button("Generar preguntas"):
        try:
            with st.spinner("Generando preguntas..."):
                questions = interview_questions(role)
        except Exception as e:
            st.error(f"Error al generar preguntas: {e}")
            return
        st.subheader("Preguntas sugeridas:")
        st.write(questions)
