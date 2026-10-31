import pytest
import requests

from talentlens.offers import scraper
from talentlens.offers.analysis import MAX_OFFER_CHARS, analyze_job_offer
from talentlens.offers.scraper import OfferFetchError, check_not_blocked, fetch_offer, parse_html
from tests.conftest import FakeResponse

LONG_TEXT = "Requisitos: Python y SQL. " * 40

OFFER_HTML = f"""<html><head><title>Portal</title><script>var tracking = 1;</script></head>
<body>
  <nav>Inicio Empresas Iniciar sesión</nav>
  <h1>Analista de datos</h1>
  <p>{LONG_TEXT}</p>
  <footer>Aviso legal</footer>
</body></html>""".encode()


def test_parse_html_keeps_offer_text_and_drops_menus_scripts_and_footers():
    title, text = parse_html(OFFER_HTML)
    assert title == "Analista de datos"
    assert "Requisitos: Python y SQL." in text
    for noise in ("tracking", "Iniciar sesión", "Aviso legal"):
        assert noise not in text


def test_parse_html_uses_page_title_when_there_is_no_h1():
    assert parse_html(b"<html><head><title>Oferta</title></head><body><p>x</p></body></html>")[0] == "Oferta"


@pytest.mark.parametrize("page", ["Nuestro sistema ha detectado actividad sospechosa", "Please complete the CAPTCHA"])
def test_block_pages_are_rejected(page):
    with pytest.raises(OfferFetchError, match="bloqueado"):
        check_not_blocked(("Aviso", page))


def test_fetch_offer_reads_static_pages_without_browser(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse(content=OFFER_HTML))
    monkeypatch.setattr(scraper, "_fetch_with_browser", lambda url: pytest.fail("no debería abrir el navegador"))
    title, text = fetch_offer("https://empleo.example/oferta")
    assert title == "Analista de datos" and "Python y SQL" in text


def test_fetch_offer_uses_browser_when_page_needs_javascript(monkeypatch):
    loading_page = FakeResponse(content=b"<html><body>Cargando</body></html>")
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: loading_page)
    monkeypatch.setattr(scraper, "_fetch_with_browser", lambda url: ("Puesto", LONG_TEXT))
    assert fetch_offer("https://empleo.example/oferta") == ("Puesto", LONG_TEXT)


def test_fetch_offer_explains_what_to_do_when_nothing_works(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.ConnectionError("sin conexión")

    def no_chrome(url):
        raise RuntimeError("Chrome no instalado")

    monkeypatch.setattr(requests, "get", fail)
    monkeypatch.setattr(scraper, "_fetch_with_browser", no_chrome)
    with pytest.raises(OfferFetchError, match="Subir un archivo"):
        fetch_offer("https://empleo.example/oferta")


def test_fetch_offer_does_not_return_block_pages_from_the_browser(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse(status_code=403))
    monkeypatch.setattr(scraper, "_fetch_with_browser", lambda url: ("Aviso", "actividad sospechosa detectada"))
    with pytest.raises(OfferFetchError, match="bloqueado"):
        fetch_offer("https://empleo.example/oferta")


def test_analysis_truncates_very_long_offers(fake_llm):
    analyze_job_offer("x" * (MAX_OFFER_CHARS + 500))
    assert "x" * MAX_OFFER_CHARS in fake_llm.calls[0]["prompt"]
    assert "x" * (MAX_OFFER_CHARS + 1) not in fake_llm.calls[0]["prompt"]
