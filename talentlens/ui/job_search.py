"""Página «Buscar empleo»: ofertas de Adzuna para un CV, valoradas por la IA."""

from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from talentlens.db import APPLICATIONS, ATS_CVS, DBManager
from talentlens.files import SUPPORTED_EXTENSIONS
from talentlens.jobs import applications
from talentlens.jobs.search import extract_search_profile, score_offers, search_jobs_for_titles
from talentlens.ui.common import fetch, read_uploaded, save

SESSION_CV = "CV optimizado de esta sesión"
SAVED_CV = "CV optimizado guardado"
UPLOAD_CV = "Subir un CV"
DAYS_OPTIONS = [7, 15, 30, 60]


def render(db: DBManager) -> None:
    st.header("Buscar empleo para tu CV")
    st.write("Busca ofertas en la API oficial de Adzuna y la IA puntúa cuánto encaja cada una con tu CV. "
             "La inscripción la haces tú en la web de la empresa o del portal.")

    cv_text, cv_label = _choose_cv(db)
    if not cv_text:
        return

    profile = _search_profile(cv_text, cv_label)
    if profile:
        _search_form(cv_text, cv_label, profile)

    results = st.session_state.get("job_results")
    if results and results["cv_label"] == cv_label:
        _render_results(db, cv_label, results)


def _choose_cv(db: DBManager) -> Tuple[Optional[str], Optional[str]]:
    """Deja elegir el CV con el que buscar. Devuelve su texto y un nombre para identificarlo."""
    sources = [SAVED_CV, UPLOAD_CV]
    if st.session_state.get("cv_result", {}).get("ats_cv"):
        sources.insert(0, SESSION_CV)
    source = st.radio("¿Con qué CV quieres buscar?", sources)

    if source == SESSION_CV:
        result = st.session_state["cv_result"]
        return result["ats_cv"], f"CV ATS - {result.get('target_role') or 'sin puesto objetivo'}"

    if source == SAVED_CV:
        saved_cvs = fetch(db, ATS_CVS)
        if saved_cvs == []:
            st.info("Todavía no hay CVs optimizados guardados. Genera uno en «Revisar CV» o sube un CV.")
        if not saved_cvs:
            return None, None
        labels = {
            f"CV ATS - {doc.get('target_role') or 'sin puesto objetivo'} "
            f"({doc['_id'].generation_time:%d/%m/%Y %H:%M})": doc
            for doc in saved_cvs
        }
        label = st.selectbox("CV guardado", list(labels))
        return labels[label]["ats_cv"], label

    uploaded = st.file_uploader("Sube tu CV (texto, PDF o Word)", type=list(SUPPORTED_EXTENSIONS))
    if not uploaded:
        return None, None
    try:
        return read_uploaded(uploaded), uploaded.name
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None, None


def _search_profile(cv_text: str, cv_label: str) -> Optional[Dict[str, Any]]:
    """La IA propone puestos, palabras clave y ubicación (una vez por CV)."""
    profile = st.session_state.get("job_profile")
    if profile and profile["cv_label"] == cv_label:
        return profile
    try:
        with st.spinner("Analizando tu CV para preparar la búsqueda..."):
            profile = {"cv_label": cv_label, **extract_search_profile(cv_text)}
    except Exception as e:
        st.error(f"Error al analizar el CV: {e}")
        return None
    st.session_state["job_profile"] = profile
    return profile


def _search_form(cv_text: str, cv_label: str, profile: Dict[str, Any]) -> None:
    """Formulario de búsqueda editable y llamada a Adzuna + valoración con IA."""
    st.subheader("Qué buscar")
    if profile["palabras_clave"]:
        st.caption("Palabras clave del CV: " + ", ".join(profile["palabras_clave"]))
    titles_text = st.text_input(
        "Puestos a buscar (separados por comas)", ", ".join(profile["puestos"]),
        help="Mejor títulos cortos y genéricos: Adzuna solo devuelve ofertas que contienen todas las palabras.",
    )
    col_where, col_days = st.columns(2)
    where = col_where.text_input("Ubicación (vacío = toda España)", profile["ubicacion"])
    max_days = col_days.selectbox("Publicadas en los últimos", DAYS_OPTIONS, index=2,
                                  format_func=lambda days: f"{days} días")

    if st.button("Buscar ofertas"):
        titles = [title.strip() for title in titles_text.split(",") if title.strip()]
        try:
            with st.spinner("Buscando ofertas y valorando cuánto encajan con tu CV..."):
                offers, totals = search_jobs_for_titles(titles, where.strip(), max_days)
                offers = score_offers(cv_text, offers)
        except Exception as e:
            st.error(f"Error al buscar ofertas: {e}")
            return
        st.session_state["job_results"] = {"cv_label": cv_label, "offers": offers, "totals": totals}


def _format_count(count: int) -> str:
    return f"{count:,}".replace(",", ".")


def _render_results(db: DBManager, cv_label: str, results: Dict[str, Any]) -> None:
    """Lista de ofertas con su valoración, enlaces y botón para marcarlas como postuladas."""
    offers: List[Dict[str, Any]] = results["offers"]
    saved = fetch(db, APPLICATIONS, {"cv_label": cv_label})
    applied = {a.get("adzuna_id") for a in saved or []}

    st.subheader(f"{len(offers)} ofertas valoradas")
    if results.get("totals"):
        st.caption("Ofertas en Adzuna por puesto: "
                   + " · ".join(f"{title}: {_format_count(count)}" for title, count in results["totals"].items())
                   + ". Se valoran las más recientes de cada puesto.")
    if not offers:
        st.info("No hay ofertas con esos criterios. Prueba con otros puestos, otra ubicación o más días.")
        return

    min_score = st.slider("Encaje mínimo", 0, 100, 0, step=10, format="%d %%")
    visible = [offer for offer in offers if offer["score"] >= min_score]
    st.caption(f"Mostrando {len(visible)} de {len(offers)} ofertas.")

    for offer in visible:
        st.markdown(f"#### {offer['score']} % · {offer['title']}")
        details = [offer["company"], offer["location"], f"publicada el {offer['created']}"]
        if offer.get("salary_min"):
            details.append(f"salario desde {_format_count(round(offer['salary_min']))} €")
        st.caption(" · ".join(detail for detail in details if detail))
        st.write(offer["reason"])
        with st.expander("Descripción"):
            st.write(offer["description"])
        st.markdown(f"1. [Web de la empresa]({offer['company_url']}) · "
                    f"2. [Ver la oferta y postular]({offer['offer_url']})")

        if offer["adzuna_id"] in applied:
            st.success("Ya la has marcado como postulada. Sigue su estado en «Mis candidaturas».")
        elif st.button("Marcar como postulada", key=f"apply_{offer['adzuna_id']}"):
            save(db, APPLICATIONS, applications.from_offer(offer, cv_label),
                 f"Candidatura a {offer['company']} guardada en «Mis candidaturas».")
        st.divider()
