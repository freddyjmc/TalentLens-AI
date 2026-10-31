import lxml.html
import requests

# Algunas webs de empleo rechazan peticiones sin un navegador conocido
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}
# Por debajo de este texto se considera que la página necesita JavaScript para mostrar la oferta
MIN_TEXT_CHARS = 500
# Frases de las páginas que muestran las webs cuando bloquean el acceso automático
BLOCK_MARKERS = (
    "actividad sospechosa", "captcha", "verify you are human", "are you a robot", "access denied",
    "just a moment", "acceso denegado", "unusual traffic",
)


def _check_not_blocked(result):
    """Evita analizar como oferta la página de bloqueo de una web."""
    title, text = result
    if any(marker in f"{title}\n{text[:1000]}".lower() for marker in BLOCK_MARKERS):
        raise RuntimeError(
            "La web ha bloqueado la lectura automática de la oferta. Ábrela en tu navegador, copia el texto "
            "en un .txt y usa «Subir un archivo»."
        )
    return result


def _fetch_static(url):
    """Descarga la página sin navegador y devuelve su título y su texto visible."""
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    doc = lxml.html.fromstring(response.content)
    for element in doc.xpath("//script | //style | //noscript | //nav | //footer | //header"):
        element.drop_tree()
    h1 = doc.xpath("//h1")
    title = h1[0].text_content().strip() if h1 else (doc.findtext(".//title") or "").strip()
    lines = (line.strip() for line in doc.text_content().splitlines())
    return title or "Título no encontrado", "\n".join(line for line in lines if line)


def _fetch_with_browser(url):
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
        page_text = driver.find_element(By.TAG_NAME, "body").text
    finally:
        driver.quit()
    return title, page_text


def fetch_offer(url):
    """Devuelve el título y el texto de una oferta.

    Primero la lee sin navegador (rápido y funciona en Docker); si la página necesita JavaScript,
    prueba con Chrome. Si tampoco es posible, explica qué hacer.
    """
    static_error = None
    try:
        static_result = _check_not_blocked(_fetch_static(url))
        if len(static_result[1]) >= MIN_TEXT_CHARS:
            return static_result
    except requests.RequestException as e:
        static_error = e

    try:
        browser_result = _fetch_with_browser(url)
    except Exception:
        browser_result = None
    if browser_result:
        return _check_not_blocked(browser_result)

    reason = (f"la web no permitió leerla ({static_error})" if static_error
              else "la página necesita un navegador para mostrar la oferta")
    raise RuntimeError(
        f"No se pudo leer la oferta: {reason} y Chrome no está disponible "
        "(por ejemplo, dentro de Docker). Copia el texto de la oferta en un .txt y usa «Subir un archivo»."
    )
