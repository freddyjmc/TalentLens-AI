from datetime import date

import mongomock
import pandas as pd
import pytest

from talentlens.db import APPLICATIONS, DBManager
from talentlens.jobs import applications

TODAY = date(2026, 10, 31)
OFFER = {
    "adzuna_id": "42", "company": "Gestoría Sol", "title": "Contable", "location": "Valencia",
    "description": "x" * 500, "company_url": "https://empresa", "offer_url": "https://oferta", "score": 85,
}


def test_application_from_offer_starts_as_applied_today():
    application = applications.from_offer(OFFER, "CV ATS - Contable", today=TODAY)
    assert application["status"] == "Postulada"
    assert application["applied_at"] == "2026-10-31"
    assert application["source"] == "Adzuna"
    assert len(application["description"]) == applications.DESCRIPTION_CHARS


def test_manual_application_requires_company_and_title():
    with pytest.raises(ValueError):
        applications.manual("  ", "Contable")
    application = applications.manual(" Gestoría Sol ", " Contable ", today=TODAY)
    assert (application["company"], application["title"], application["cv_label"]) == (
        "Gestoría Sol", "Contable", "Sin CV indicado")


def test_changed_rows_only_reports_edited_status_or_notes():
    original = pd.DataFrame({"status": ["Postulada", "Postulada"], "notes": ["", "llamar"], "company": ["A", "B"]},
                            index=["id1", "id2"])
    edited = original.copy()
    edited.at["id1", "status"] = "Entrevista"
    assert applications.changed_rows(original, edited) == {"id1": {"status": "Entrevista", "notes": ""}}


def test_count_by_status_includes_every_status_in_order():
    counts = applications.count_by_status([{"status": "Vista"}, {"status": "Vista"}, {"status": "Aceptada"}])
    assert list(counts) == applications.STATUSES
    assert counts["Vista"] == 2 and counts["Aceptada"] == 1 and counts["Postulada"] == 0


def test_db_manager_crud_with_in_memory_mongo():
    db = DBManager("mongodb://test", "asistente", client=mongomock.MongoClient())
    db.save_data(APPLICATIONS, {"company": "A", "status": "Postulada"})
    db.save_data(APPLICATIONS, {"company": "B", "status": "Postulada"})

    db.update_data(APPLICATIONS, {"company": "A"}, {"status": "Vista"})
    assert [d["status"] for d in db.fetch_data(APPLICATIONS, {"company": "A"})] == ["Vista"]

    db.delete_data(APPLICATIONS, {"company": "B"})
    assert [d["company"] for d in db.fetch_data(APPLICATIONS)] == ["A"]


def test_db_manager_requires_configuration():
    with pytest.raises(ValueError, match="MONGODB_URI"):
        DBManager.from_settings()
