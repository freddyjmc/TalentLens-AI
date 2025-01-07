import openai
from config import configure_openai
from pymongo import MongoClient

# Configurar OpenAI
configure_openai()

# Inicializar cliente de MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["asistente"]

def review_cv(cv_text):
    """Revisa un CV y proporciona comentarios sobre su efectividad."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un experto en revisión de CVs."},
                {"role": "user", "content": f"Revisa este CV:\n{cv_text}\n¿Pasaría pruebas ATS? Proporciona sugerencias para mejorarlo."}
            ],
            max_tokens=500
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error al revisar el CV: {e}"


