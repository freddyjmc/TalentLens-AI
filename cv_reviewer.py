import openai
from config import OPENAI_MAX_TOKENS, OPENAI_MODEL, configure_openai

# Configurar OpenAI
configure_openai()

def review_cv(cv_text):
    """Revisa un CV y proporciona comentarios sobre su efectividad."""
    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Eres un experto en revisión de CVs."},
            {"role": "user", "content": f"Revisa este CV:\n{cv_text}\n¿Pasaría pruebas ATS? Proporciona sugerencias para mejorarlo."}
        ],
        max_tokens=OPENAI_MAX_TOKENS
    )
    return response['choices'][0]['message']['content'].strip()


