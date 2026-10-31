import streamlit as st

from talentlens.db import DBManager


def render(db: DBManager) -> None:
    st.header("Bienvenido a TalentLens AI")
    st.write("Tu plataforma para mejorar tu CV, buscar ofertas que encajen con él, "
             "llevar el control de tus candidaturas y practicar entrevistas.")
