# utils/config.py
import openai
import os
from dotenv import load_dotenv

def configure_openai():
    load_dotenv()  # Cargar variables de entorno
    openai.api_key = os.getenv("OPENAI_API_KEY")
