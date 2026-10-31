"""Página «Mis candidaturas»: panel de seguimiento por CV."""

import pandas as pd
import streamlit as st
from bson import ObjectId

from talentlens.db import APPLICATIONS, DBManager
from talentlens.jobs import applications
from talentlens.ui.common import DB_UNAVAILABLE, fetch, save

ALL_CVS = "Todos los CVs"
VISIBLE_COLUMNS = ["status", "applied_at", "company", "title", "location", "cv_label",
                   "company_url", "offer_url", "notes", "description"]
COLUMN_CONFIG = {
    "status": st.column_config.SelectboxColumn("Estado", options=applications.STATUSES, required=True),
    "applied_at": st.column_config.TextColumn("Fecha"),
    "company": st.column_config.TextColumn("Empresa"),
    "title": st.column_config.TextColumn("Puesto"),
    "location": st.column_config.TextColumn("Ubicación"),
    "cv_label": st.column_config.TextColumn("CV"),
    "company_url": st.column_config.LinkColumn("Web empresa"),
    "offer_url": st.column_config.LinkColumn("Oferta"),
    "notes": st.column_config.TextColumn("Notas"),
    "description": st.column_config.TextColumn("Descripción"),
}


def render(db: DBManager) -> None:
    st.header("Mis candidaturas")
    _manual_form(db)

    saved = fetch(db, APPLICATIONS)
    if saved is None:
        return
    if not saved:
        st.info("Aún no tienes candidaturas. Márcalas como postuladas desde «Buscar empleo» o añádelas a mano.")
        return

    cv_labels = sorted({a.get("cv_label", "") for a in saved})
    selected_cv = st.selectbox("CV", [ALL_CVS] + cv_labels)
    if selected_cv != ALL_CVS:
        saved = [a for a in saved if a.get("cv_label") == selected_cv]

    # Resumen por estado
    for column, (status, count) in zip(st.columns(len(applications.STATUSES)),
                                       applications.count_by_status(saved).items()):
        column.metric(status, count)

    df = pd.DataFrame(saved)
    df["_id"] = df["_id"].astype(str)
    original = df.set_index("_id").reindex(columns=VISIBLE_COLUMNS).fillna("")
    edited = st.data_editor(
        original,
        column_config=COLUMN_CONFIG,
        disabled=[c for c in VISIBLE_COLUMNS if c not in applications.EDITABLE_FIELDS],
        hide_index=True,
        use_container_width=True,
        key="applications_editor",
    )

    if st.button("Guardar cambios"):
        changes = applications.changed_rows(original, edited)
        try:
            for app_id, values in changes.items():
                db.update_data(APPLICATIONS, {"_id": ObjectId(app_id)}, values)
        except Exception as e:
            st.error(f"{DB_UNAVAILABLE} ({e})")
            return
        st.success(f"Cambios guardados en {len(changes)} candidatura(s).")


def _manual_form(db: DBManager) -> None:
    """Formulario para añadir una candidatura encontrada fuera de la aplicación."""
    with st.expander("Añadir una candidatura a mano"), st.form("manual_application", clear_on_submit=True):
        company = st.text_input("Empresa")
        title = st.text_input("Puesto")
        offer_url = st.text_input("Enlace a la oferta")
        cv_label = st.text_input("CV usado", placeholder="Ej.: CV ATS - Data Analyst")
        notes = st.text_area("Notas")
        if st.form_submit_button("Añadir"):
            try:
                application = applications.manual(company, title, offer_url, cv_label, notes)
            except ValueError as e:
                st.warning(str(e))
                return
            save(db, APPLICATIONS, application, "Candidatura añadida. Recarga la sección para verla en la tabla.")
