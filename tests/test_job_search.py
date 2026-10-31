import re

import pytest
import requests

from talentlens.jobs import search
from talentlens.jobs.search import (
    NO_SCORE_REASON,
    SCORE_BATCH_SIZE,
    JobSearchError,
    extract_search_profile,
    parse_adzuna_job,
    score_offers,
    search_jobs,
    search_jobs_for_titles,
    simplify_title,
)
from tests.conftest import FakeResponse


def _adzuna_job(job_id, title="Contable", company="Empresa"):
    return {
        "id": job_id, "title": f" {title} ", "company": {"display_name": company},
        "location": {"display_name": "Valencia"}, "description": "Contabilidad general",
        "created": "2026-10-30T08:00:00Z", "salary_min": 22000, "redirect_url": f"https://adzuna.example/{job_id}",
    }


@pytest.mark.parametrize("title, expected", [
    ("Administrativo contable junior", "Administrativo contable"),
    ("Data Analyst (Junior)", "Data Analyst"),
    ("Auxiliar contable en prácticas", "Auxiliar contable"),
    ("Senior Data Engineer", "Data Engineer"),
    ("Contable", "Contable"),
])
def test_simplify_title_removes_words_that_restrict_the_search(title, expected):
    assert simplify_title(title) == expected


def test_profile_simplifies_titles_and_limits_lists(fake_llm):
    fake_llm.json_response = {
        "puestos": ["Contable junior", "Administrativo", "Auxiliar contable", "Técnico contable", "Asistente", "Extra"],
        "palabras_clave": [f"k{i}" for i in range(10)],
        "ubicacion": None,
    }
    profile = extract_search_profile("CV")
    assert profile["puestos"] == ["Contable", "Administrativo", "Auxiliar contable", "Técnico contable", "Asistente"]
    assert len(profile["palabras_clave"]) == 6
    assert profile["ubicacion"] == ""


def test_parse_adzuna_job_builds_links_and_cleans_fields():
    offer = parse_adzuna_job(_adzuna_job(7, company="Gestoría Sol"))
    assert offer["adzuna_id"] == "7"
    assert offer["title"] == "Contable"
    assert offer["created"] == "2026-10-30"
    assert offer["offer_url"] == "https://adzuna.example/7"
    assert offer["company_url"].startswith("https://www.google.com/search?q=Gestor%C3%ADa+Sol+trabaja")


def test_parse_adzuna_job_handles_missing_company():
    assert parse_adzuna_job({"id": 1})["company"] == "Empresa no indicada"


def test_search_requires_adzuna_credentials():
    with pytest.raises(JobSearchError, match="ADZUNA_APP_ID"):
        search_jobs("Contable")


def test_search_sends_filters_and_returns_offers_and_total(set_env, monkeypatch):
    set_env(ADZUNA_APP_ID="id", ADZUNA_APP_KEY="key")
    sent = {}

    def fake_get(url, params, timeout):
        sent.update(url=url, **params)
        return FakeResponse(json_data={"count": 770, "results": [_adzuna_job(1), _adzuna_job(2)]})

    monkeypatch.setattr(requests, "get", fake_get)
    offers, total = search_jobs("Contable", "Valencia", max_days_old=15, results=2)

    assert total == 770
    assert [o["adzuna_id"] for o in offers] == ["1", "2"]
    assert sent["url"].endswith("/jobs/es/search/1")
    filters = (sent["what"], sent["where"], sent["max_days_old"], sent["results_per_page"])
    assert filters == ("Contable", "Valencia", 15, 2)


def test_search_reports_adzuna_errors(set_env, monkeypatch):
    set_env(ADZUNA_APP_ID="id", ADZUNA_APP_KEY="mala")
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(401, {"display": "Authorisation failed"}))
    with pytest.raises(JobSearchError, match="401: Authorisation failed"):
        search_jobs("Contable")


def test_search_for_titles_removes_duplicates_and_reports_totals(monkeypatch):
    results = {"Contable": ([parse_adzuna_job(_adzuna_job(1)), parse_adzuna_job(_adzuna_job(2))], 770),
               "Auxiliar contable": ([parse_adzuna_job(_adzuna_job(2)), parse_adzuna_job(_adzuna_job(3))], 68)}
    monkeypatch.setattr(search, "search_jobs", lambda title, *args: results[title])

    offers, totals = search_jobs_for_titles(["Contable junior", "Contable", "Auxiliar contable", " "])

    assert [o["adzuna_id"] for o in offers] == ["1", "2", "3"]
    assert totals == {"Contable": 770, "Auxiliar contable": 68}


def test_score_offers_in_batches_sorts_and_handles_missing_scores(fake_llm):
    offers = [{"adzuna_id": str(i), "title": f"Puesto {i}", "company": "E", "location": "", "description": ""}
              for i in range(SCORE_BATCH_SIZE + 5)]

    def answer(prompt):
        # Puntuación = número del puesto (fuera de rango en algunos casos); la oferta 0 de cada tanda sin valorar
        numbers = [int(n) for n in re.findall(r"\] Puesto (\d+)", prompt)]
        return {"ofertas": [{"indice": i, "puntuacion": n * 10, "motivo": f"motivo {n}"}
                            for i, n in enumerate(numbers) if i > 0]}

    fake_llm.json_response = answer
    scored = score_offers("CV", offers)

    assert len(fake_llm.calls) == 2  # 25 ofertas -> dos tandas
    assert [o["score"] for o in scored] == sorted((o["score"] for o in scored), reverse=True)
    assert all(0 <= o["score"] <= 100 for o in scored)
    unscored = [o for o in scored if o["reason"] == NO_SCORE_REASON]
    assert {o["adzuna_id"] for o in unscored} == {"0", str(SCORE_BATCH_SIZE)}
