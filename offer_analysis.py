import openai
from config import configure_openai
from pymongo import MongoClient

# Configurar OpenAI
configure_openai()

# Inicializar cliente de MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["asistente"]

def analyze_job_offer(text):
    """Analiza una oferta de empleo y devuelve un resumen con habilidades y palabras clave."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un analista de ofertas de empleo."},
                {"role": "user", "content": f"Analiza esta oferta de empleo:\n{text}\nExtrae habilidades necesarias, palabras clave, y un resumen breve."}
            ],
            max_tokens=500
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error al analizar la oferta: {e}"


