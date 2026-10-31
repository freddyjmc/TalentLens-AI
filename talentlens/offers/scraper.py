"""Lectura de una oferta de empleo a partir de su enlace."""

from __future__ import annotations

from typing import Optional, Tuple

import lxml.html
import requests

# Algunas webs de empleo rechazan peticiones sin un navegador conocido
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}
REQUEST_TIMEOUT = 20
# Por debajo de este texto se considera que la página necesita JavaScript para mostrar la oferta
MIN_TEXT_CHARS = 500
# Frases de las páginas que muestran las webs cuando bloquean el acceso automático
BLOCK_MARKERS = (
    "actividad sospechosa", "captcha", "verify you are human", "are you a robot", "access denied",
    "just a moment", "acceso denegado", "unusual traffic",
)

Offer = Tuple[str, str]  # (título, texto)


class OfferFetchError(RuntimeError):
    """No se pudo leer la oferta; el mensaje explica qué puede hacer el usuario."""


def parse_html(html: bytes) -> Offer:
    """Extrae el título y el texto visible de una página, sin menús, scripts ni pies de página."""
    doc = lxml.html.fromstring(html)
    for element in doc.xpath("//script | //style | //noscript | //nav | //footer | //header"):
        element.drop_tree()
    h1 = doc.xpath("//h1")
    title = h1[0].text_content().strip() if h1 else (doc.findtext(".//title") or "").strip()
    lines = (line.strip() for line in doc.text_content().splitlines())
    return title or "Título no encontrado", "\n".join(line for line in lines if line)


def check_not_blocked(offer: Offer) -> Offer:
    """Evita analizar como oferta la página de bloqueo de una web."""
    title, text = offer
    if any(marker in f"{title}\n{text[:1000]}".lower() for marker in BLOCK_MARKERS):
        raise OfferFetchError(
            "La web ha bloqueado la lectura automática de la oferta. Ábrela en tu navegador, copia el texto "
            "en un .txt y usa «Subir un archivo»."
        )
    return offer


def _fetch_static(url: str) -> Offer:
    """Descarga la página sin navegador."""
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return parse_html(response.content)


def _fetch_with_browser(url: str) -> Offer:
    """Abre la página con Chrome en modo headless (solo funciona si Chrome está instalado)."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Selenium Manager descarga el driver que corresponde a la versión de Chrome instalada
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        h1 = driver.find_elements(By.TAG_NAME, "h1")
        title = h1[0].text if h1 else "Título no encontrado"
        return title, driver.find_element(By.TAG_NAME, "body").text
    finally:
        driver.quit()


def fetch_offer(url: str) -> Offer:
    """Devuelve el título y el texto de una oferta.

    Primero la lee sin navegador (rápido y funciona en Docker); si la página necesita JavaScript,
    prueba con Chrome. Si tampoco es posible, lanza `OfferFetchError` explicando qué hacer.
    """
    static_error: Optional[Exception] = None
    try:
        offer = check_not_blocked(_fetch_static(url))
        if len(offer[1]) >= MIN_TEXT_CHARS:
            return offer
    except requests.RequestException as e:
        static_error = e

    try:
        browser_offer = _fetch_with_browser(url)
    except Exception:  # Chrome no instalado, driver incompatible, timeout...
        browser_offer = None
    if browser_offer:
        return check_not_blocked(browser_offer)

    reason = (f"la web no permitió leerla ({static_error})" if static_error
              else "la página necesita un navegador para mostrar la oferta")
    raise OfferFetchError(
        f"No se pudo leer la oferta: {reason} y Chrome no está disponible "
        "(por ejemplo, dentro de Docker). Copia el texto de la oferta en un .txt y usa «Subir un archivo»."
    )
