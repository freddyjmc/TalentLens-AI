"""Generación de una versión del CV optimizada para filtros ATS."""

from talentlens import llm
from talentlens.config import get_settings

SYSTEM_PROMPT = "Eres un experto en redacción de CVs y sistemas ATS."

# Formato que se pide a la IA: sencillo para que lo lean los ATS y fácil de exportar
ATS_INSTRUCTIONS = """Reescribe este CV para que pase filtros ATS (Applicant Tracking Systems).

Reglas:
- No inventes nada: ni empresas, ni puestos, ni fechas, ni títulos, ni cifras, ni datos de contacto,
  ni tareas, logros, resultados, tecnologías o conocimientos que el CV original no mencione.
- Cada punto debe poder justificarse con una frase del CV original. Puedes reordenar y redactar mejor
  (verbos de acción, palabras clave estándar del sector), pero no añadir contenido.
- Si falta un dato importante (contacto, fechas, empresa, logros medibles), escribe [COMPLETAR: qué falta].
- Conserva los datos del original aunque sean breves (por ejemplo, la duración de una experiencia).
- Conserva los niveles de idioma tal cual aparecen (por ejemplo "Inglés: básico (A2)").
- Corrige ortografía y puntuación, elimina repeticiones (también en nombres de centros o empresas)
  y usa un estilo profesional e impersonal: "Orientación a resultados" mejor que "Estoy orientado a los logros".
- Sé conciso: si el contenido cabe en una página, no lo alargues.
- Una sola columna, sin tablas, sin iconos ni emojis.
- Escribe en el mismo idioma que el CV original.

Formato de salida (solo el CV, sin comentarios antes ni después):
# Nombre completo
Datos de contacto en una línea
## Perfil profesional
## Experiencia
## Formación
## Habilidades
## Proyectos (si hay)
## Idiomas (si hay)
Usa "## " para cada sección, "### " para cada puesto o estudio y "- " para cada punto."""


def build_prompt(cv_text: str, target_role: str = "") -> str:
    """Construye la petición a la IA, con el puesto objetivo si se indica."""
    prompt = f"{ATS_INSTRUCTIONS}\n\nCV original:\n{cv_text}"
    if target_role.strip():
        prompt += (f"\n\nPuesto objetivo: {target_role.strip()}. "
                   "Prioriza las palabras clave de ese puesto que el CV justifique.")
    return prompt


def generate_ats_cv(cv_text: str, target_role: str = "") -> str:
    """Genera una versión del CV optimizada para filtros ATS, sin inventar datos."""
    return llm.ask(
        SYSTEM_PROMPT,
        build_prompt(cv_text, target_role),
        max_tokens=get_settings().openai_max_tokens * 2,
        temperature=0.2,  # poca creatividad: reescribir, no inventar
    )
