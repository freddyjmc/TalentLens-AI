import io
import json
import re

import openai
from pypdf import PdfReader

from config import OPENAI_MAX_TOKENS, OPENAI_MODEL, configure_openai

# Configurar OpenAI
configure_openai()

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"\+?\d[\d\s.-]{7,}\d")
LANGUAGE_LEVEL_RE = re.compile(r"\b[ABC][12]\b")


def _digits(text):
    return re.sub(r"\D", "", text)


def check_rules(original, ats_cv, pdf_bytes):
    """Comprobaciones automáticas (sin IA). Devuelve una lista de (correcto, mensaje)."""
    checks = []

    # El PDF debe ocupar una página (o dos bien llenas) y su texto debe poder extraerse
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = len(reader.pages)
    checks.append((pages == 1, f"El PDF ocupa {pages} página(s)."))
    pdf_words = len(" ".join(page.extract_text() or "" for page in reader.pages).split())
    cv_words = len(ats_cv.replace("#", " ").replace("**", " ").split())
    checks.append((pdf_words >= 0.9 * cv_words,
                   f"Texto extraíble del PDF: {pdf_words} de {cv_words} palabras."))

    # Datos de contacto y niveles de idioma del original que deben conservarse
    for email in set(EMAIL_RE.findall(original)):
        ok = email in ats_cv
        checks.append((ok, f"Email {email}: {'conservado' if ok else 'no aparece en el CV generado'}."))
    for phone in set(PHONE_RE.findall(original)):
        if len(_digits(phone)) < 9:
            continue  # rangos de años como "2019 - 2023", no teléfonos
        ok = _digits(phone) in _digits(ats_cv)
        checks.append((ok, f"Teléfono {phone.strip()}: {'conservado' if ok else 'no aparece en el CV generado'}."))
    for level in sorted(set(LANGUAGE_LEVEL_RE.findall(original))):
        ok = level in ats_cv
        checks.append((ok, f"Nivel de idioma {level}: {'conservado' if ok else 'no aparece en el CV generado'}."))

    pending = ats_cv.count("[COMPLETAR")
    checks.append((pending == 0, f"Campos por completar: {pending}."))
    return checks


def check_with_ai(original, ats_cv):
    """Segunda revisión con IA: compara el CV generado con el original."""
    prompt = f"""Compara el CV ORIGINAL con el CV GENERADO. El GENERADO es una reescritura para filtros ATS:
reformular frases, unir puntos repetidos, quitar repeticiones y mejorar el estilo es correcto y NO es un error.

Devuelve solo un JSON con tres listas de frases cortas en español:
- "inventado": hechos del GENERADO que no están en el ORIGINAL (empresas, puestos, fechas, títulos, cifras,
  tecnologías, tareas o logros nuevos).
- "perdido": hechos concretos del ORIGINAL que no aparecen de ninguna forma en el GENERADO (empresas, puestos,
  fechas, títulos, tecnologías, proyectos, idiomas y niveles, datos de contacto). Una frase eliminada por repetida
  o reformulada no está perdida. Los campos [COMPLETAR] no cuentan.
- "estilo": errores reales del GENERADO (faltas de ortografía, puntuación incorrecta, palabras repetidas).
  No compares con el ORIGINAL ni propongas preferencias de redacción.
Antes de añadir un elemento, comprueba en el texto que es cierto. Si no hay nada en una lista, déjala vacía.

CV ORIGINAL:
{original}

CV GENERADO:
{ats_cv}"""
    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Eres un revisor estricto de CVs. Respondes solo con JSON."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=OPENAI_MAX_TOKENS,
        temperature=0,
        response_format={"type": "json_object"}
    )
    result = json.loads(response['choices'][0]['message']['content'])
    return {key: list(result.get(key, [])) for key in ("inventado", "perdido", "estilo")}
