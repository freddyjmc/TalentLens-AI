"""Verificación del CV generado: reglas automáticas y una segunda revisión con IA."""

from __future__ import annotations

import io
import re
from typing import Dict, List, NamedTuple

from pypdf import PdfReader

from talentlens import llm

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"\+?\d[\d\s.-]{7,}\d")
LANGUAGE_LEVEL_RE = re.compile(r"\b[ABC][12]\b")
MIN_PHONE_DIGITS = 9  # por debajo suelen ser rangos de años como "2019 - 2023"
MIN_EXTRACTED_RATIO = 0.9

AI_CHECK_KEYS = ("inventado", "perdido", "estilo")
AI_SYSTEM_PROMPT = "Eres un revisor estricto de CVs. Respondes solo con JSON."
AI_INSTRUCTIONS = """Compara el CV ORIGINAL con el CV GENERADO. El GENERADO es una reescritura para filtros ATS:
reformular frases, unir puntos repetidos, quitar repeticiones y mejorar el estilo es correcto y NO es un error.

Devuelve solo un JSON con tres listas de frases cortas en español:
- "inventado": hechos del GENERADO que no están en el ORIGINAL (empresas, puestos, fechas, títulos, cifras,
  tecnologías, tareas o logros nuevos).
- "perdido": hechos concretos del ORIGINAL que no aparecen de ninguna forma en el GENERADO (empresas, puestos,
  fechas, títulos, tecnologías, proyectos, idiomas y niveles, datos de contacto). Una frase eliminada por repetida
  o reformulada no está perdida. Los campos [COMPLETAR] no cuentan.
- "estilo": errores reales del GENERADO (faltas de ortografía, puntuación incorrecta, palabras repetidas).
  No compares con el ORIGINAL ni propongas preferencias de redacción.
Antes de añadir un elemento, comprueba en el texto que es cierto. Si no hay nada en una lista, déjala vacía."""


class Check(NamedTuple):
    ok: bool
    message: str


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def _kept(ok: bool) -> str:
    return "conservado" if ok else "no aparece en el CV generado"


def check_rules(original: str, ats_cv: str, pdf_bytes: bytes) -> List[Check]:
    """Comprobaciones automáticas, sin IA."""
    checks: List[Check] = []

    # El PDF debe ocupar una página y su texto debe poder extraerse
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = len(reader.pages)
    checks.append(Check(pages == 1, f"El PDF ocupa {pages} página(s)."))
    pdf_words = len(" ".join(page.extract_text() or "" for page in reader.pages).split())
    cv_words = len(ats_cv.replace("#", " ").replace("**", " ").split())
    checks.append(Check(pdf_words >= MIN_EXTRACTED_RATIO * cv_words,
                        f"Texto extraíble del PDF: {pdf_words} de {cv_words} palabras."))

    # Datos de contacto y niveles de idioma del original que deben conservarse
    for email in sorted(set(EMAIL_RE.findall(original))):
        ok = email in ats_cv
        checks.append(Check(ok, f"Email {email}: {_kept(ok)}."))
    for phone in sorted(set(PHONE_RE.findall(original))):
        if len(_digits(phone)) < MIN_PHONE_DIGITS:
            continue
        ok = _digits(phone) in _digits(ats_cv)
        checks.append(Check(ok, f"Teléfono {phone.strip()}: {_kept(ok)}."))
    for level in sorted(set(LANGUAGE_LEVEL_RE.findall(original))):
        ok = level in ats_cv
        checks.append(Check(ok, f"Nivel de idioma {level}: {_kept(ok)}."))

    pending = ats_cv.count("[COMPLETAR")
    checks.append(Check(pending == 0, f"Campos por completar: {pending}."))
    return checks


def check_with_ai(original: str, ats_cv: str) -> Dict[str, List[str]]:
    """Segunda revisión con IA: datos inventados, datos perdidos y errores de estilo."""
    prompt = f"{AI_INSTRUCTIONS}\n\nCV ORIGINAL:\n{original}\n\nCV GENERADO:\n{ats_cv}"
    result = llm.ask_json(AI_SYSTEM_PROMPT, prompt, temperature=0)
    return {key: [str(item) for item in result.get(key, [])] for key in AI_CHECK_KEYS}
