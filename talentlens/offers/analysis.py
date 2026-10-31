"""Análisis de una oferta de empleo con IA."""

from talentlens import llm

SYSTEM_PROMPT = "Eres un analista de ofertas de empleo."
# Límite de caracteres de una oferta que se envían a la IA (las páginas web pueden ser muy largas)
MAX_OFFER_CHARS = 8000


def analyze_job_offer(text: str) -> str:
    """Extrae puesto, empresa, ubicación, habilidades, palabras clave y un resumen de la oferta."""
    prompt = (f"Analiza esta oferta de empleo:\n{text[:MAX_OFFER_CHARS]}\n"
              "Indica el puesto, la empresa y la ubicación si aparecen. "
              "Extrae habilidades necesarias, palabras clave, y un resumen breve.")
    return llm.ask(SYSTEM_PROMPT, prompt)
