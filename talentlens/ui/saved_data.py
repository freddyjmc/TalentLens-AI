"""Página «Datos guardados»: tablas de cada colección y descarga en CSV."""

import pandas as pd
import streamlit as st

from talentlens.db import ATS_CVS, CV_REVIEWS, JOB_OFFERS, DBManager
from talentlens.ui.common import fetch

# Tipo de datos -> (colección de MongoDB, nombre del CSV)
COLLECTIONS = {
    "Ofertas de empleo": (JOB_OFFERS, "ofertas_guardadas.csv"),
    "Revisiones de CV": (CV_REVIEWS, "revisiones_cv.csv"),
    "CVs optimizados para ATS": (ATS_CVS, "cvs_optimizados.csv"),
}


def render(db: DBManager) -> None:
    st.header("Datos Guardados")
    data_type = st.selectbox("Selecciona el tipo de datos", list(COLLECTIONS))
    collection, csv_name = COLLECTIONS[data_type]

    data = fetch(db, collection)
    if data is None:
        return
    if not data:
        st.warning(f"No hay datos guardados en la colección '{collection}'.")
        return

    df = pd.DataFrame(data).drop(columns=["_id"], errors="ignore")
    st.write(f"Se encontraron {len(data)} registros:")
    st.dataframe(df)
    st.download_button("Descargar como CSV", data=df.to_csv(index=False).encode("utf-8"),
                       file_name=csv_name, mime="text/csv")
