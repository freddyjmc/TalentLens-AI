"""Revisión de un CV con IA."""

from talentlens import llm

SYSTEM_PROMPT = "Eres un experto en revisión de CVs."


def review_cv(cv_text: str) -> str:
    """Valora si el CV pasaría filtros ATS y propone mejoras."""
    prompt = f"Revisa este CV:\n{cv_text}\n¿Pasaría pruebas ATS? Proporciona sugerencias para mejorarlo."
    return llm.ask(SYSTEM_PROMPT, prompt)
