# utils/config.py
import openai
import os
from dotenv import load_dotenv

load_dotenv()

# Modelo de OpenAI (gpt-3.5-turbo está retirado)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
# Máximo de tokens por respuesta (con menos, las respuestas largas se cortaban)
OPENAI_MAX_TOKENS = 1000

def configure_openai():
    load_dotenv()  # Cargar variables de entorno
    openai.api_key = os.getenv("OPENAI_API_KEY")
