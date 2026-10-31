"""Página «Revisar CV»: revisión, CV optimizado para ATS, verificación y descargas."""

from typing import Any, Dict

import streamlit as st

from talentlens.cv.export import to_docx, to_pdf, to_txt
from talentlens.cv.generator import generate_ats_cv
from talentlens.cv.review import review_cv
from talentlens.cv.verifier import check_rules, check_with_ai
from talentlens.db import ATS_CVS, CV_REVIEWS, DBManager
from talentlens.files import SUPPORTED_EXTENSIONS
from talentlens.ui.common import file_key, read_uploaded, save

AI_CHECK_TITLES = {
    "inventado": "Posibles datos inventados",
    "perdido": "Datos del original que faltan",
    "estilo": "Ortografía y estilo",
}
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def render(db: DBManager) -> None:
    st.header("Revisión de CV")
    uploaded = st.file_uploader("Sube tu CV (texto, PDF o Word)", type=list(SUPPORTED_EXTENSIONS))
    if not uploaded:
        return

    current_source = file_key(uploaded)
    result = st.session_state.get("cv_result")
    # Revisar solo cuando cambia el archivo, no en cada recarga de la página
    if not result or result["source"] != current_source:
        try:
            cv_text = read_uploaded(uploaded)
            with st.spinner("Revisando el CV..."):
                review = review_cv(cv_text)
            result = {"source": current_source, "text": cv_text, "review": review}
            st.session_state["cv_result"] = result
        except Exception as e:
            st.error(f"Error al revisar el CV: {e}")
            return

    st.subheader("Revisión del CV:")
    st.write(result["review"])
    if st.button("Guardar revisión"):
        save(db, CV_REVIEWS, {"text": result["text"], "review": result["review"]},
             "Revisión guardada en la base de datos")

    st.divider()
    _render_ats_cv(db, result)


def _render_ats_cv(db: DBManager, result: Dict[str, Any]) -> None:
    """Genera la versión del CV para ATS, la verifica y ofrece descargarla y guardarla."""
    st.subheader("CV optimizado para ATS")
    target_role = st.text_input("Puesto objetivo (opcional)", placeholder="Ej.: Data Scientist Junior").strip()
    if st.button("Generar CV optimizado"):
        try:
            with st.spinner("Generando el CV optimizado..."):
                ats_cv = generate_ats_cv(result["text"], target_role)
            ats_pdf = to_pdf(ats_cv)
            with st.spinner("Verificando el CV generado..."):
                ai_checks = check_with_ai(result["text"], ats_cv)
            result.update(ats_cv=ats_cv, target_role=target_role, ats_pdf=ats_pdf,
                          rule_checks=check_rules(result["text"], ats_cv, ats_pdf), ai_checks=ai_checks)
        except Exception as e:
            st.error(f"Error al generar o verificar el CV: {e}")

    if not result.get("ats_cv"):
        return

    st.info("Revisa el CV antes de enviarlo y rellena los campos marcados con [COMPLETAR].")
    st.markdown(result["ats_cv"])

    with st.expander("Verificación del CV generado", expanded=True):
        for check in result.get("rule_checks", []):
            (st.success if check.ok else st.warning)(check.message)
        for key, title in AI_CHECK_TITLES.items():
            items = result.get("ai_checks", {}).get(key, [])
            if items:
                st.warning(f"**{title}:**\n" + "\n".join(f"- {item}" for item in items))
            else:
                st.success(f"{title}: ninguno detectado.")
        st.caption("Comprobación práctica, no una prueba contra un ATS concreto.")

    col_pdf, col_docx, col_txt = st.columns(3)
    col_pdf.download_button("Descargar PDF", data=result["ats_pdf"], file_name="cv_ats.pdf", mime="application/pdf")
    col_docx.download_button("Descargar Word", data=to_docx(result["ats_cv"]), file_name="cv_ats.docx",
                             mime=DOCX_MIME)
    col_txt.download_button("Descargar TXT", data=to_txt(result["ats_cv"]), file_name="cv_ats.txt",
                            mime="text/plain")

    if st.button("Guardar CV optimizado"):
        save(db, ATS_CVS, {
            "target_role": result.get("target_role", ""),
            "ats_cv": result["ats_cv"],
            "original": result["text"],
        }, "CV optimizado guardado en la base de datos")
