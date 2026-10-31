"""Búsqueda de ofertas en la API oficial de Adzuna y valoración con IA de cuánto encajan con un CV."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import quote_plus

import requests

from talentlens import llm
from talentlens.config import get_settings

Offer = Dict[str, Any]

ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
REQUEST_TIMEOUT = 20
# Caracteres de cada descripción que se envían a la IA para puntuar (las de Adzuna ya vienen recortadas)
MAX_DESCRIPTION_CHARS = 400
# Ofertas que se piden por cada puesto y ofertas que se puntúan en cada llamada a la IA
OFFERS_PER_TITLE = 20
SCORE_BATCH_SIZE = 20
MAX_SEARCH_TITLES = 5
# Adzuna exige que la oferta contenga todas las palabras: estas restringen demasiado la búsqueda
RESTRICTIVE_WORDS = re.compile(
    r"\b(junior|júnior|jr|senior|sénior|sr|trainee|becario|becaria|en prácticas|prácticas|practicas)\b",
    re.IGNORECASE,
)

PROFILE_SYSTEM_PROMPT = "Eres un orientador laboral. Respondes solo con JSON."
PROFILE_INSTRUCTIONS = """A partir de este CV, devuelve solo un JSON con:
- "puestos": 5 títulos de puesto para buscar en portales de empleo de España, del más al menos adecuado.
  Deben ser cortos (1 a 3 palabras) y genéricos, tal como aparecen en los anuncios, sin nivel de experiencia
  (nada de "junior" o "senior") ni especialidades. Incluye sinónimos y variantes habituales, en español o en
  inglés según se publiquen en ese sector (por ejemplo: "Contable", "Administrativo contable", "Auxiliar contable",
  "Técnico contable", "Administrativo"; o "Data Analyst", "Analista de datos", "Business Analyst").
- "palabras_clave": hasta 6 tecnologías o competencias del CV.
- "ubicacion": la ciudad del candidato si aparece en el CV, o "" si no aparece."""

SCORE_SYSTEM_PROMPT = "Eres un reclutador técnico. Respondes solo con JSON."
SCORE_INSTRUCTIONS = """Puntúa de 0 a 100 cuánto encaja cada oferta con el CV, siendo realista
(experiencia exigida, tecnologías, sector). Devuelve solo un JSON con la lista "ofertas", con un elemento por
oferta: {"indice": número, "puntuacion": número, "motivo": "una frase con lo que encaja y lo que falta"}.
Cada motivo debe entenderse solo, sin mencionar otras ofertas ni sus números."""
NO_SCORE_REASON = "Sin valoración."


class JobSearchError(RuntimeError):
    """Error al consultar la API de Adzuna."""


def simplify_title(title: str) -> str:
    """Quita del título el nivel de experiencia y los paréntesis para no perder ofertas."""
    title = re.sub(r"\(.*?\)", " ", title)
    title = RESTRICTIVE_WORDS.sub(" ", title)
    return re.sub(r"\s+", " ", title).strip(" -/,")


def extract_search_profile(cv_text: str) -> Dict[str, Any]:
    """Deduce del CV los puestos a buscar, las palabras clave y la ubicación."""
    profile = llm.ask_json(PROFILE_SYSTEM_PROMPT, f"{PROFILE_INSTRUCTIONS}\n\nCV:\n{cv_text}", temperature=0)
    titles = [simplify_title(str(t)) for t in profile.get("puestos", [])]
    return {
        "puestos": [t for t in titles if t][:MAX_SEARCH_TITLES],
        "palabras_clave": [str(k) for k in profile.get("palabras_clave", [])][:6],
        "ubicacion": str(profile.get("ubicacion") or ""),
    }


def parse_adzuna_job(job: Dict[str, Any]) -> Offer:
    """Convierte una oferta de la respuesta de Adzuna al formato que usa la aplicación."""
    company = (job.get("company") or {}).get("display_name") or "Empresa no indicada"
    return {
        "adzuna_id": str(job.get("id")),
        "title": (job.get("title") or "").strip(),
        "company": company,
        "location": (job.get("location") or {}).get("display_name", ""),
        "description": (job.get("description") or "").strip(),
        "created": (job.get("created") or "")[:10],
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "offer_url": job.get("redirect_url", ""),
        # Adzuna no da la web de la empresa: se enlaza una búsqueda de su página de empleo
        "company_url": "https://www.google.com/search?q=" + quote_plus(f"{company} trabaja con nosotros"),
    }


def search_jobs(
    what: str, where: str = "", max_days_old: int = 30, results: int = OFFERS_PER_TITLE, country: str = "es"
) -> Tuple[List[Offer], int]:
    """Busca ofertas en Adzuna. Devuelve las más recientes y el total disponible para esa búsqueda."""
    settings = get_settings()
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        raise JobSearchError("ADZUNA_APP_ID o ADZUNA_APP_KEY no están configurados en el archivo .env.")
    params = {
        "app_id": settings.adzuna_app_id, "app_key": settings.adzuna_app_key, "what": what,
        "results_per_page": results, "max_days_old": max_days_old, "sort_by": "date",
    }
    if where:
        params["where"] = where
    response = requests.get(ADZUNA_URL.format(country=country), params=params, timeout=REQUEST_TIMEOUT)
    if response.status_code != 200:
        try:
            detail = response.json().get("display", "")
        except ValueError:
            detail = response.text[:200]
        raise JobSearchError(f"Adzuna respondió {response.status_code}: {detail}")

    data = response.json()
    offers = [parse_adzuna_job(job) for job in data.get("results", [])]
    return offers, int(data.get("count", len(offers)))


def search_jobs_for_titles(
    titles: Iterable[str], where: str = "", max_days_old: int = 30, per_title: int = OFFERS_PER_TITLE
) -> Tuple[List[Offer], Dict[str, int]]:
    """Busca varios puestos y une los resultados sin duplicados.

    Devuelve las ofertas y, para cada puesto buscado, cuántas tiene Adzuna en total.
    """
    offers: List[Offer] = []
    seen: set = set()
    totals: Dict[str, int] = {}
    unique_titles = dict.fromkeys(t for t in (simplify_title(title) for title in titles) if t)
    for title in unique_titles:
        found, totals[title] = search_jobs(title, where, max_days_old, per_title)
        for offer in found:
            if offer["adzuna_id"] not in seen:
                seen.add(offer["adzuna_id"])
                offers.append(offer)
    return offers, totals


def _score_batch(cv_text: str, offers: List[Offer]) -> None:
    """Puntúa una tanda de ofertas, añadiendo a cada una "score" y "reason"."""
    listing = "\n".join(
        f'[{i}] {o["title"]} | {o["company"]} | {o["location"]} | {o["description"][:MAX_DESCRIPTION_CHARS]}'
        for i, o in enumerate(offers)
    )
    prompt = f"{SCORE_INSTRUCTIONS}\n\nCV:\n{cv_text}\n\nOFERTAS:\n{listing}"
    result = llm.ask_json(SCORE_SYSTEM_PROMPT, prompt, temperature=0,
                          max_tokens=get_settings().openai_max_tokens * 2)
    scores = {item.get("indice"): item for item in result.get("ofertas", []) if isinstance(item, dict)}
    for i, offer in enumerate(offers):
        item = scores.get(i, {})
        offer["score"] = max(0, min(100, int(item.get("puntuacion") or 0)))
        offer["reason"] = item.get("motivo") or NO_SCORE_REASON


def score_offers(cv_text: str, offers: List[Offer]) -> List[Offer]:
    """Puntúa de 0 a 100 cuánto encaja cada oferta con el CV y las ordena de mejor a peor.

    Se puntúan por tandas en paralelo para que muchas ofertas no superen el límite de respuesta de la IA.
    """
    batches = [offers[i:i + SCORE_BATCH_SIZE] for i in range(0, len(offers), SCORE_BATCH_SIZE)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda batch: _score_batch(cv_text, batch), batches))
    return sorted(offers, key=lambda offer: offer["score"], reverse=True)
