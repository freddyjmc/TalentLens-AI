import openai
from config import OPENAI_MAX_TOKENS, OPENAI_MODEL, configure_openai

# Configurar OpenAI
configure_openai()

def analyze_job_offer(text):
    """Analiza una oferta de empleo y devuelve un resumen con habilidades y palabras clave."""
    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Eres un analista de ofertas de empleo."},
            {"role": "user", "content": f"Analiza esta oferta de empleo:\n{text}\nIndica el puesto, la empresa y la ubicación si aparecen. Extrae habilidades necesarias, palabras clave, y un resumen breve."}
        ],
        max_tokens=OPENAI_MAX_TOKENS
    )
    return response['choices'][0]['message']['content'].strip()


