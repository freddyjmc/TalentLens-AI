import io
import os
from datetime import date

import openai
import pandas as pd
import streamlit as st
from bson import ObjectId
from docx import Document
from dotenv import load_dotenv
from pypdf import PdfReader

from config import OPENAI_MAX_TOKENS, OPENAI_MODEL
from cv_export import to_docx, to_pdf, to_txt
from cv_generator import generate_ats_cv
from cv_reviewer import review_cv
from cv_verifier import check_rules, check_with_ai
from db_manager import DBManager
from job_search import extract_search_profile, score_offers, search_jobs_for_titles
from offer_analysis import analyze_job_offer
from offer_scraper import fetch_offer

# Cargar variables de entorno
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicializar DBManager (configuración cargada desde .env)
db_manager = DBManager()

# Límite de caracteres de una página web que se envían a la IA
MAX_PAGE_CHARS = 8000

# Estados de una candidatura en el panel de seguimiento
APPLICATION_STATUSES = ["Postulada", "Vista", "Entrevista", "Descartada", "Aceptada"]


def read_uploaded_text(uploaded_file):
    """Devuelve el texto de un archivo .txt, .pdf o .docx subido."""
    data = uploaded_file.getvalue()
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def save_to_db(collection, data, success_message):
    """Guarda en MongoDB y muestra un mensaje claro si la base de datos no responde."""
    try:
        db_manager.save_data(collection, data)
        st.success(success_message)
    except Exception as e:
        st.error(f"No se pudo guardar en la base de datos. ¿Está MongoDB en marcha? ({e})")


def file_key(uploaded_file):
    """Identifica un archivo subido para no repetir el análisis en cada recarga."""
    return f"{uploaded_file.name}-{uploaded_file.size}"


# Configuración inicial
st.title("TalentLens AI - Tu Asistente de Búsqueda de Empleo")

# Opciones del menú
menu = st.sidebar.selectbox(
    "Selecciona una opción",
    ["Inicio", "Analizar ofertas", "Revisar CV", "Buscar empleo", "Mis candidaturas",
     "Practicar entrevistas", "Datos guardados", "Asistente Inteligente"]
)

if menu == "Inicio":
    st.header("Bienvenido a TalentLens AI")
    st.write("Tu plataforma para mejorar tu CV, buscar ofertas que encajen con él, "
             "llevar el control de tus candidaturas y practicar entrevistas.")

elif menu == "Analizar ofertas":
    st.header("Análisis de Ofertas de Empleo")
    option = st.radio("Selecciona el método para analizar la oferta:", ["Pegar un enlace", "Subir un archivo"])

    if option == "Pegar un enlace":
        url = st.text_input("Pega el enlace a la oferta de empleo")
        if url and st.button("Analizar oferta"):
            try:
                with st.spinner("Leyendo y analizando la oferta..."):
                    title, page_text = fetch_offer(url)
                    analysis = analyze_job_offer(page_text[:MAX_PAGE_CHARS])
                st.session_state["offer_result"] = {
                    "source": url,
                    "data": {"url": url, "title": title, "text": page_text, "analysis": analysis},
                }
            except Exception as e:
                st.error(f"Error al analizar la oferta: {e}")
        current_source = url

    elif option == "Subir un archivo":
        uploaded_offer = st.file_uploader("Sube una oferta de empleo (texto o PDF)", type=["txt", "pdf"])
        current_source = file_key(uploaded_offer) if uploaded_offer else None
        result = st.session_state.get("offer_result")
        if uploaded_offer and (not result or result["source"] != current_source):
            try:
                offer_text = read_uploaded_text(uploaded_offer)
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
            save_to_db("job_offers", dict(result["data"]), "Oferta guardada en la base de datos")

elif menu == "Revisar CV":
    st.header("Revisión de CV")
    uploaded_cv = st.file_uploader("Sube tu CV (texto, PDF o Word)", type=["txt", "pdf", "docx"])
    if uploaded_cv:
        current_source = file_key(uploaded_cv)
        result = st.session_state.get("cv_result")
        if not result or result["source"] != current_source:
            try:
                cv_text = read_uploaded_text(uploaded_cv)
                with st.spinner("Revisando el CV..."):
                    review = review_cv(cv_text)
                result = {"source": current_source, "text": cv_text, "review": review}
                st.session_state["cv_result"] = result
            except Exception as e:
                st.error(f"Error al revisar el CV: {e}")
                result = None

        if result:
            st.subheader("Revisión del CV:")
            st.write(result["review"])

            if st.button("Guardar revisión"):
                save_to_db("cv_reviews", {"text": result["text"], "review": result["review"]},
                           "Revisión guardada en la base de datos")

            # Generar una versión del CV optimizada para ATS a partir del CV subido
            st.divider()
            st.subheader("CV optimizado para ATS")
            target_role = st.text_input("Puesto objetivo (opcional)", placeholder="Ej.: Data Scientist Junior")
            if st.button("Generar CV optimizado"):
                try:
                    with st.spinner("Generando el CV optimizado..."):
                        result["ats_cv"] = generate_ats_cv(result["text"], target_role.strip())
                    result["target_role"] = target_role.strip()
                    result["ats_pdf"] = to_pdf(result["ats_cv"])
                    # Verificar el CV generado: reglas automáticas y una segunda revisión con IA
                    result["rule_checks"] = check_rules(result["text"], result["ats_cv"], result["ats_pdf"])
                    with st.spinner("Verificando el CV generado..."):
                        result["ai_checks"] = check_with_ai(result["text"], result["ats_cv"])
                except Exception as e:
                    st.error(f"Error al generar o verificar el CV: {e}")

            if result.get("ats_cv"):
                st.info("Revisa el CV antes de enviarlo y rellena los campos marcados con [COMPLETAR].")
                with st.container():
                    st.markdown(result["ats_cv"])

                with st.expander("Verificación del CV generado", expanded=True):
                    for ok, message in result.get("rule_checks", []):
                        (st.success if ok else st.warning)(message)
                    ai_checks = result.get("ai_checks")
                    if ai_checks:
                        titles = {
                            "inventado": "Posibles datos inventados",
                            "perdido": "Datos del original que faltan",
                            "estilo": "Ortografía y estilo",
                        }
                        for key, title in titles.items():
                            if ai_checks[key]:
                                st.warning(f"**{title}:**\n" + "\n".join(f"- {item}" for item in ai_checks[key]))
                            else:
                                st.success(f"{title}: ninguno detectado.")
                    st.caption("Comprobación práctica, no una prueba contra un ATS concreto.")

                col_pdf, col_docx, col_txt = st.columns(3)
                col_pdf.download_button(
                    "Descargar PDF", data=result.get("ats_pdf") or to_pdf(result["ats_cv"]),
                    file_name="cv_ats.pdf", mime="application/pdf",
                )
                col_docx.download_button(
                    "Descargar Word", data=to_docx(result["ats_cv"]), file_name="cv_ats.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
                col_txt.download_button(
                    "Descargar TXT", data=to_txt(result["ats_cv"]),
                    file_name="cv_ats.txt", mime="text/plain",
                )

                if st.button("Guardar CV optimizado"):
                    save_to_db("ats_cvs", {
                        "target_role": result.get("target_role", ""),
                        "ats_cv": result["ats_cv"],
                        "original": result["text"],
                    }, "CV optimizado guardado en la base de datos")

elif menu == "Buscar empleo":
    st.header("Buscar empleo para tu CV")
    st.write("Busca ofertas en la API oficial de Adzuna y la IA puntúa cuánto encaja cada una con tu CV. "
             "La inscripción la haces tú en la web de la empresa o del portal.")

    # Elegir el CV con el que buscar
    sources = []
    if st.session_state.get("cv_result", {}).get("ats_cv"):
        sources.append("CV optimizado de esta sesión")
    sources += ["CV optimizado guardado", "Subir un CV"]
    source = st.radio("¿Con qué CV quieres buscar?", sources)

    cv_text, cv_label = None, None
    if source == "CV optimizado de esta sesión":
        result = st.session_state["cv_result"]
        cv_text = result["ats_cv"]
        cv_label = f"CV ATS - {result.get('target_role') or 'sin puesto objetivo'}"
    elif source == "CV optimizado guardado":
        try:
            saved_cvs = db_manager.fetch_data("ats_cvs")
        except Exception as e:
            saved_cvs = None
            st.error(f"No se pudo leer la base de datos. ¿Está MongoDB en marcha? ({e})")
        if saved_cvs:
            labels = {
                f"CV ATS - {doc.get('target_role') or 'sin puesto objetivo'} "
                f"({doc['_id'].generation_time:%d/%m/%Y %H:%M})": doc
                for doc in saved_cvs
            }
            cv_label = st.selectbox("CV guardado", list(labels))
            cv_text = labels[cv_label]["ats_cv"]
        elif saved_cvs == []:
            st.info("Todavía no hay CVs optimizados guardados. Genera uno en «Revisar CV» o sube un CV.")
    else:
        uploaded = st.file_uploader("Sube tu CV (texto, PDF o Word)", type=["txt", "pdf", "docx"])
        if uploaded:
            try:
                cv_text = read_uploaded_text(uploaded)
                cv_label = uploaded.name
            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")

    if cv_text:
        # Paso 1: la IA propone puestos y ubicación a partir del CV
        profile = st.session_state.get("job_profile")
        if not profile or profile["cv_label"] != cv_label:
            try:
                with st.spinner("Analizando tu CV para preparar la búsqueda..."):
                    profile = {"cv_label": cv_label, **extract_search_profile(cv_text)}
                st.session_state["job_profile"] = profile
            except Exception as e:
                st.error(f"Error al analizar el CV: {e}")
                profile = None

        if profile:
            st.subheader("Qué buscar")
            if profile["palabras_clave"]:
                st.caption("Palabras clave del CV: " + ", ".join(profile["palabras_clave"]))
            titles_text = st.text_input(
                "Puestos a buscar (separados por comas)", ", ".join(profile["puestos"]),
                help="Mejor títulos cortos y genéricos: Adzuna solo devuelve ofertas que contienen todas las palabras.",
            )
            col_where, col_days = st.columns(2)
            where = col_where.text_input("Ubicación (vacío = toda España)", profile["ubicacion"])
            max_days = col_days.selectbox("Publicadas en los últimos", [7, 15, 30, 60], index=2,
                                          format_func=lambda d: f"{d} días")

            # Paso 2: buscar en Adzuna y puntuar con la IA
            if st.button("Buscar ofertas"):
                titles = [t.strip() for t in titles_text.split(",") if t.strip()]
                try:
                    with st.spinner("Buscando ofertas y valorando cuánto encajan con tu CV..."):
                        offers, totals = search_jobs_for_titles(titles, where.strip(), max_days)
                        offers = score_offers(cv_text, offers)
                    st.session_state["job_results"] = {"cv_label": cv_label, "offers": offers, "totals": totals}
                except Exception as e:
                    st.error(f"Error al buscar ofertas: {e}")

    # Paso 3: mostrar las ofertas con sus enlaces y el botón para marcarlas como postuladas
    results = st.session_state.get("job_results")
    if cv_text and results and results["cv_label"] == cv_label:
        offers = results["offers"]
        try:
            applied = {a.get("adzuna_id") for a in db_manager.fetch_data("applications", {"cv_label": cv_label})}
        except Exception:
            applied = set()
            st.warning("No se pudo leer la base de datos: no se sabe qué ofertas ya están postuladas.")

        totals = results.get("totals", {})
        st.subheader(f"{len(offers)} ofertas valoradas")
        if totals:
            st.caption("Ofertas en Adzuna por puesto: "
                       + " · ".join(f"{title}: {count:,}".replace(",", ".") for title, count in totals.items())
                       + ". Se valoran las más recientes de cada puesto.")
        if not offers:
            st.info("No hay ofertas con esos criterios. Prueba con otros puestos, otra ubicación o más días.")
            visible_offers = []
        else:
            min_score = st.slider("Encaje mínimo", 0, 100, 0, step=10, format="%d %%")
            visible_offers = [o for o in offers if o["score"] >= min_score]
            st.caption(f"Mostrando {len(visible_offers)} de {len(offers)} ofertas.")
        for offer in visible_offers:
            st.markdown(f"#### {offer['score']} % · {offer['title']}")
            details = [offer["company"], offer["location"], f"publicada el {offer['created']}"]
            if offer.get("salary_min"):
                details.append(f"salario desde {offer['salary_min']:,.0f} €".replace(",", "."))
            st.caption(" · ".join(d for d in details if d))
            st.write(offer["reason"])
            with st.expander("Descripción"):
                st.write(offer["description"])
            st.markdown(f"1. [Web de la empresa]({offer['company_url']}) · "
                        f"2. [Ver la oferta y postular]({offer['offer_url']})")

            if offer["adzuna_id"] in applied:
                st.success("Ya la has marcado como postulada. Sigue su estado en «Mis candidaturas».")
            elif st.button("Marcar como postulada", key=f"apply_{offer['adzuna_id']}"):
                save_to_db("applications", {
                    "cv_label": cv_label,
                    "adzuna_id": offer["adzuna_id"],
                    "company": offer["company"],
                    "title": offer["title"],
                    "location": offer["location"],
                    "description": offer["description"][:300],
                    "company_url": offer["company_url"],
                    "offer_url": offer["offer_url"],
                    "source": "Adzuna",
                    "score": offer["score"],
                    "status": "Postulada",
                    "applied_at": date.today().isoformat(),
                    "notes": "",
                }, f"Candidatura a {offer['company']} guardada en «Mis candidaturas».")
            st.divider()

elif menu == "Mis candidaturas":
    st.header("Mis candidaturas")
    try:
        applications = db_manager.fetch_data("applications")
    except Exception as e:
        applications = None
        st.error(f"No se pudo leer la base de datos. ¿Está MongoDB en marcha? ({e})")

    # Añadir a mano una candidatura encontrada fuera de la app
    with st.expander("Añadir una candidatura a mano"):
        with st.form("manual_application", clear_on_submit=True):
            m_company = st.text_input("Empresa")
            m_title = st.text_input("Puesto")
            m_url = st.text_input("Enlace a la oferta")
            m_cv = st.text_input("CV usado", placeholder="Ej.: CV ATS - Data Analyst")
            m_notes = st.text_area("Notas")
            if st.form_submit_button("Añadir"):
                if m_company.strip() and m_title.strip():
                    save_to_db("applications", {
                        "cv_label": m_cv.strip() or "Sin CV indicado", "adzuna_id": None,
                        "company": m_company.strip(), "title": m_title.strip(), "location": "",
                        "description": "", "company_url": "", "offer_url": m_url.strip(),
                        "source": "Manual", "score": None, "status": "Postulada",
                        "applied_at": date.today().isoformat(), "notes": m_notes.strip(),
                    }, "Candidatura añadida. Recarga la sección para verla en la tabla.")
                else:
                    st.warning("Indica al menos la empresa y el puesto.")

    if applications == []:
        st.info("Aún no tienes candidaturas. Márcalas como postuladas desde «Buscar empleo» o añádelas a mano.")
    elif applications:
        cv_labels = sorted({a.get("cv_label", "") for a in applications})
        selected_cv = st.selectbox("CV", ["Todos los CVs"] + cv_labels)
        if selected_cv != "Todos los CVs":
            applications = [a for a in applications if a.get("cv_label") == selected_cv]

        # Resumen por estado
        columns = st.columns(len(APPLICATION_STATUSES))
        for column, status in zip(columns, APPLICATION_STATUSES):
            column.metric(status, sum(1 for a in applications if a.get("status") == status))

        df = pd.DataFrame(applications)
        df["_id"] = df["_id"].astype(str)
        df = df.set_index("_id")
        visible = ["status", "applied_at", "company", "title", "location", "cv_label",
                   "company_url", "offer_url", "notes", "description"]
        original = df[visible].fillna("")
        edited = st.data_editor(
            original,
            column_config={
                "status": st.column_config.SelectboxColumn("Estado", options=APPLICATION_STATUSES, required=True),
                "applied_at": st.column_config.TextColumn("Fecha"),
                "company": st.column_config.TextColumn("Empresa"),
                "title": st.column_config.TextColumn("Puesto"),
                "location": st.column_config.TextColumn("Ubicación"),
                "cv_label": st.column_config.TextColumn("CV"),
                "company_url": st.column_config.LinkColumn("Web empresa"),
                "offer_url": st.column_config.LinkColumn("Oferta"),
                "notes": st.column_config.TextColumn("Notas"),
                "description": st.column_config.TextColumn("Descripción"),
            },
            disabled=[c for c in visible if c not in ("status", "notes")],
            hide_index=True,
            use_container_width=True,
            key="applications_editor",
        )

        if st.button("Guardar cambios"):
            changed = 0
            try:
                for app_id in edited.index:
                    new, old = edited.loc[app_id], original.loc[app_id]
                    if new["status"] != old["status"] or (new["notes"] or "") != (old["notes"] or ""):
                        db_manager.update_data("applications", {"_id": ObjectId(app_id)},
                                               {"status": new["status"], "notes": new["notes"] or ""})
                        changed += 1
                st.success(f"Cambios guardados en {changed} candidatura(s).")
            except Exception as e:
                st.error(f"No se pudieron guardar los cambios. ¿Está MongoDB en marcha? ({e})")

elif menu == "Practicar entrevistas":
    st.header("Práctica de Entrevistas")
    role = st.text_input("Ingresa el rol para el que deseas practicar")
    if role and st.button("Generar preguntas"):
        try:
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Eres un entrenador de entrevistas laborales."},
                    {"role": "user", "content": f"Genera 5 preguntas comunes para el rol de {role}."}
                ],
                max_tokens=OPENAI_MAX_TOKENS
            )
            st.subheader("Preguntas sugeridas:")
            st.write(response['choices'][0]['message']['content'])
        except Exception as e:
            st.error(f"Error al generar preguntas: {e}")

elif menu == "Datos guardados":
    st.header("Datos Guardados")
    # Tipo de datos -> (colección de MongoDB, nombre del CSV)
    collections = {
        "Ofertas de empleo": ("job_offers", "ofertas_guardadas.csv"),
        "Revisiones de CV": ("cv_reviews", "revisiones_cv.csv"),
        "CVs optimizados para ATS": ("ats_cvs", "cvs_optimizados.csv"),
    }
    data_type = st.selectbox("Selecciona el tipo de datos", list(collections))
    collection, csv_name = collections[data_type]

    try:
        # Recuperar datos de MongoDB
        data = db_manager.fetch_data(collection)

        if data:
            # Convertir datos a un DataFrame para mostrar como tabla
            df = pd.DataFrame(data)

            # Eliminar la columna '_id' para evitar ruido visual
            if "_id" in df.columns:
                df = df.drop(columns=["_id"])

            st.write(f"Se encontraron {len(data)} registros:")
            st.dataframe(df)

            # Botón para descargar como CSV
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Descargar como CSV",
                data=csv,
                file_name=csv_name,
                mime="text/csv",
            )
        else:
            st.warning(f"No hay datos guardados en la colección '{collection}'.")
    except Exception as e:
        st.error(f"Error al recuperar datos: {e}")


elif menu == "Asistente Inteligente":
    st.header("Asistente Inteligente")
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "system", "content": "Eres un asistente experto en trabajo, CVs y desarrollo profesional."}
        ]

    # Mostrar historial de mensajes (sin el mensaje de sistema)
    for msg in st.session_state["messages"]:
        if msg["role"] == "system":
            continue
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Escribe tu pregunta o solicitud")
    if user_input and user_input.strip():
        # Agregar mensaje del usuario al historial
        st.session_state["messages"].append({"role": "user", "content": user_input.strip()})
        with st.chat_message("user"):
            st.write(user_input.strip())
        try:
            # Generar respuesta de OpenAI
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=st.session_state["messages"],
                max_tokens=OPENAI_MAX_TOKENS
            )
            answer = response['choices'][0]['message']['content'].strip()
            st.session_state["messages"].append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.write(answer)
        except Exception as e:
            # Quitar la pregunta sin respuesta para no reenviarla en la siguiente llamada
            st.session_state["messages"].pop()
            st.error(f"Error al procesar la solicitud: {e}")
