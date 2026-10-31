import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus

import openai
import requests
from dotenv import load_dotenv

from config import OPENAI_MAX_TOKENS, OPENAI_MODEL, configure_openai

# Configurar OpenAI y cargar las credenciales de Adzuna
configure_openai()
load_dotenv()

ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
# Caracteres de cada descripción que se envían a la IA para puntuar (las de Adzuna ya vienen recortadas)
MAX_DESCRIPTION_CHARS = 400
# Ofertas que se piden por cada puesto y ofertas que se puntúan en cada llamada a la IA
OFFERS_PER_TITLE = 20
SCORE_BATCH_SIZE = 20
# Adzuna exige que la oferta contenga todas las palabras: estas restringen demasiado la búsqueda
RESTRICTIVE_WORDS = r"\b(junior|júnior|jr|senior|sénior|sr|trainee|becario|becaria|prácticas|practicas|en prácticas)\b"


def simplify_title(title):
    """Quita del título el nivel de experiencia y los paréntesis para no perder ofertas."""
    title = re.sub(r"\(.*?\)", " ", title)
    title = re.sub(RESTRICTIVE_WORDS, " ", title, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", title).strip(" -/,")


def _ask_json(system, prompt):
    """Llama a OpenAI y devuelve la respuesta como JSON."""
    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        max_tokens=OPENAI_MAX_TOKENS * 2,
        temperature=0,
        response_format={"type": "json_object"}
    )
    return json.loads(response['choices'][0]['message']['content'])


def extract_search_profile(cv_text):
    """Deduce del CV los puestos a buscar, las palabras clave y la ubicación."""
    prompt = f"""A partir de este CV, devuelve solo un JSON con:
- "puestos": 5 títulos de puesto para buscar en portales de empleo de España, del más al menos adecuado.
  Deben ser cortos (1 a 3 palabras) y genéricos, tal como aparecen en los anuncios, sin nivel de experiencia
  (nada de "junior" o "senior") ni especialidades. Incluye sinónimos y variantes habituales, en español o en
  inglés según se publiquen en ese sector (por ejemplo: "Contable", "Administrativo contable", "Auxiliar contable",
  "Técnico contable", "Administrativo"; o "Data Analyst", "Analista de datos", "Business Analyst").
- "palabras_clave": hasta 6 tecnologías o competencias del CV.
- "ubicacion": la ciudad del candidato si aparece en el CV, o "" si no aparece.

CV:
{cv_text}"""
    profile = _ask_json("Eres un orientador laboral. Respondes solo con JSON.", prompt)
    return {
        "puestos": [simplify_title(t) for t in profile.get("puestos", [])][:5],
        "palabras_clave": list(profile.get("palabras_clave", []))[:6],
        "ubicacion": profile.get("ubicacion", "") or "",
    }


def search_jobs(what, where="", max_days_old=30, results=OFFERS_PER_TITLE, country="es"):
    """Busca ofertas en la API oficial de Adzuna.

    Devuelve las ofertas más recientes en un formato sencillo y el total que tiene Adzuna para esa búsqueda.
    """
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        raise ValueError("ADZUNA_APP_ID o ADZUNA_APP_KEY no están configurados en el archivo .env.")
    params = {
        "app_id": app_id.strip(), "app_key": app_key.strip(), "what": what,
        "results_per_page": results, "max_days_old": max_days_old, "sort_by": "date",
    }
    if where:
        params["where"] = where
    response = requests.get(ADZUNA_URL.format(country=country), params=params, timeout=20)
    if response.status_code != 200:
        detail = response.json().get("display", response.text[:200]) if response.content else ""
        raise RuntimeError(f"Adzuna respondió {response.status_code}: {detail}")

    data = response.json()
    offers = []
    for job in data.get("results", []):
        company = job.get("company", {}).get("display_name", "") or "Empresa no indicada"
        offers.append({
            "adzuna_id": str(job.get("id")),
            "title": job.get("title", "").strip(),
            "company": company,
            "location": job.get("location", {}).get("display_name", ""),
            "description": job.get("description", "").strip(),
            "created": job.get("created", "")[:10],
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "offer_url": job.get("redirect_url", ""),
            # Adzuna no da la web de la empresa: se enlaza una búsqueda de su página de empleo
            "company_url": "https://www.google.com/search?q=" + quote_plus(f"{company} trabaja con nosotros"),
        })
    return offers, data.get("count", len(offers))


def search_jobs_for_titles(titles, where="", max_days_old=30, per_title=OFFERS_PER_TITLE):
    """Busca varios puestos y une los resultados sin duplicados.

    Devuelve las ofertas y, para cada puesto buscado, cuántas tiene Adzuna en total.
    """
    offers, seen, totals = [], set(), {}
    for title in dict.fromkeys(simplify_title(t) for t in titles if simplify_title(t)):
        found, totals[title] = search_jobs(title, where, max_days_old, per_title)
        for offer in found:
            if offer["adzuna_id"] not in seen:
                seen.add(offer["adzuna_id"])
                offers.append(offer)
    return offers, totals


def score_offers(cv_text, offers):
    """Puntúa de 0 a 100 cuánto encaja cada oferta con el CV y las ordena de mejor a peor.

    Se puntúan por tandas en paralelo para que muchas ofertas no superen el límite de respuesta de la IA.
    """
    batches = [offers[i:i + SCORE_BATCH_SIZE] for i in range(0, len(offers), SCORE_BATCH_SIZE)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda batch: _score_batch(cv_text, batch), batches))
    return sorted(offers, key=lambda o: o["score"], reverse=True)


def _score_batch(cv_text, offers):
    """Puntúa una tanda de ofertas (modifica cada oferta añadiendo "score" y "reason")."""
    listing = "\n".join(
        f'[{i}] {o["title"]} | {o["company"]} | {o["location"]} | {o["description"][:MAX_DESCRIPTION_CHARS]}'
        for i, o in enumerate(offers)
    )
    prompt = f"""Puntúa de 0 a 100 cuánto encaja cada oferta con el CV, siendo realista
(experiencia exigida, tecnologías, sector). Devuelve solo un JSON con la lista "ofertas", con un elemento por
oferta: {{"indice": número, "puntuacion": número, "motivo": "una frase con lo que encaja y lo que falta"}}.
Cada motivo debe entenderse solo, sin mencionar otras ofertas ni sus números.

CV:
{cv_text}

OFERTAS:
{listing}"""
    result = _ask_json("Eres un reclutador técnico. Respondes solo con JSON.", prompt)
    scores = {item.get("indice"): item for item in result.get("ofertas", [])}
    for i, offer in enumerate(offers):
        item = scores.get(i, {})
        offer["score"] = int(item.get("puntuacion", 0) or 0)
        offer["reason"] = item.get("motivo", "Sin valoración.")
