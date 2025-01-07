import streamlit as st
import openai
import os
from db_manager import DBManager
from offer_analysis import analyze_job_offer
from cv_reviewer import review_cv
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
from random import choice

# Cargar variables de entorno
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicializar DBManager (configuración cargada desde .env)
db_manager = DBManager()

# Configuración inicial
st.title("JobMate - Tu Asistente de Búsqueda de Empleo")

# Opciones del menú
menu = st.sidebar.selectbox(
    "Selecciona una opción",
    ["Inicio", "Analizar ofertas", "Revisar CV", "Practicar entrevistas", "Datos guardados", "Asistente Inteligente"]
)

if menu == "Inicio":
    st.header("Bienvenido a JobMate")
    st.write("Tu plataforma para analizar ofertas, practicar entrevistas y mejorar tu CV.")

elif menu == "Analizar ofertas":
    st.header("Análisis de Ofertas de Empleo")
    option = st.radio("Selecciona el método para analizar la oferta:", ["Pegar un enlace", "Subir un archivo"])

    if option == "Pegar un enlace":
        url = st.text_input("Pega el enlace a la oferta de empleo")
        if url and st.button("Analizar oferta"):
            try:
                # Configuración de Selenium
                options = Options()
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")

                driver = webdriver.Chrome(
                    service=webdriver.chrome.service.Service(ChromeDriverManager().install()), options=options
                )
                driver.get(url)

                # Extraer datos básicos
                title = driver.find_element(By.TAG_NAME, "h1").text if driver.find_elements(By.TAG_NAME, "h1") else "Título no encontrado"
                company = driver.find_element(By.TAG_NAME, "a").text if driver.find_elements(By.TAG_NAME, "a") else "Empresa no encontrada"
                location = driver.find_element(By.TAG_NAME, "span").text if driver.find_elements(By.TAG_NAME, "span") else "Ubicación no encontrada"

                # Extraer descripción del trabajo
                description = ""
                description_elements = driver.find_elements(By.TAG_NAME, "p")
                if description_elements:
                    description = "\n".join([desc.text for desc in description_elements if desc.text.strip()])
                if not description:
                    description = "Descripción no encontrada"

                driver.quit()

                # Mostrar la información extraída
                st.subheader("Datos básicos de la oferta:")
                st.write(f"**Título del empleo:** {title}")
                st.write(f"**Empresa:** {company}")
                st.write(f"**Ubicación:** {location}")
                st.write(f"**Descripción del trabajo:** {description[:500]}...")

                # Guardar en MongoDB
                if st.button("Guardar análisis"):
                    offer_data = {
                        "url": url,
                        "title": title,
                        "company": company,
                        "location": location,
                        "description": description,
                    }
                    db_manager.save_data("job_offers", offer_data)
                    st.success("Oferta guardada en la base de datos")

            except Exception as e:
                st.error(f"Error al procesar el enlace: {e}")

    elif option == "Subir un archivo":
        uploaded_offer = st.file_uploader("Sube una oferta de empleo (texto o PDF)", type=["txt", "pdf"])
        if uploaded_offer:
            offer_text = uploaded_offer.read().decode("utf-8")
            analysis = analyze_job_offer(offer_text)
            st.subheader("Análisis de la oferta:")
            st.write(analysis)

            if st.button("Guardar análisis"):
                db_manager.save_data("job_offers", {"text": offer_text, "analysis": analysis})
                st.success("Oferta guardada en la base de datos")

elif menu == "Revisar CV":
    st.header("Revisión de CV")
    uploaded_cv = st.file_uploader("Sube tu CV (texto o PDF)", type=["txt", "pdf"])
    if uploaded_cv:
        try:
            cv_text = uploaded_cv.read().decode("utf-8")
        except UnicodeDecodeError:
            cv_text = uploaded_cv.read().decode("latin-1")

        review = review_cv(cv_text)
        st.subheader("Revisión del CV:")
        st.write(review)

        if st.button("Guardar revisión"):
            db_manager.save_data("cv_reviews", {"text": cv_text, "review": review})
            st.success("Revisión guardada en la base de datos")

elif menu == "Practicar entrevistas":
    st.header("Práctica de Entrevistas")
    role = st.text_input("Ingresa el rol para el que deseas practicar")
    if role and st.button("Generar preguntas"):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un entrenador de entrevistas laborales."},
                    {"role": "user", "content": f"Genera 5 preguntas comunes para el rol de {role}."}
                ],
                max_tokens=300
            )
            st.subheader("Preguntas sugeridas:")
            st.write(response['choices'][0]['message']['content'])
        except Exception as e:
            st.error(f"Error al generar preguntas: {e}")

elif menu == "Datos guardados":
    st.header("Datos Guardados")
    data_type = st.selectbox("Selecciona el tipo de datos", ["Ofertas de empleo"])

    if data_type == "Ofertas de empleo":
        try:
            # Recuperar datos de MongoDB
            data = db_manager.fetch_data("job_offers")

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
                    file_name="ofertas_guardadas.csv",
                    mime="text/csv",
                )
            else:
                st.warning("No hay datos guardados en la colección 'job_offers'.")
        except Exception as e:
            st.error(f"Error al recuperar datos: {e}")


elif menu == "Asistente Inteligente":
    st.header("Asistente Inteligente")
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "system", "content": "Eres un asistente experto en trabajo, CVs y desarrollo profesional."}
        ]

    # Mostrar historial de mensajes
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state["messages"]:
            role = "Usuario" if msg["role"] == "user" else "Asistente"
            st.write(f"**{role}:** {msg['content'].strip()}")

    # Fijar la barra de preguntas en la parte inferior
    with st.form(key="chat_input_form", clear_on_submit=True):
        user_input = st.text_input("Escribe tu pregunta o solicitud:")
        submit_button = st.form_submit_button("Enviar")

    if submit_button and user_input.strip():
        # Agregar mensaje del usuario al historial
        st.session_state["messages"].append({"role": "user", "content": user_input.strip()})
        try:
            # Generar respuesta de OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=st.session_state["messages"],
                max_tokens=500
            )
            # Agregar respuesta del asistente al historial
            st.session_state["messages"].append(response['choices'][0]['message'])
        except Exception as e:
            st.error(f"Error al procesar la solicitud: {e}")

        # Actualizar la vista del historial
        with chat_container:
            for msg in st.session_state["messages"]:
                role = "Usuario" if msg["role"] == "user" else "Asistente"
                st.write(f"**{role}:** {msg['content'].strip()}")





