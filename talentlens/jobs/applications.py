"""Candidaturas: creación y detección de cambios en el panel de seguimiento."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

import pandas as pd

Application = Dict[str, Any]

STATUSES = ["Postulada", "Vista", "Entrevista", "Descartada", "Aceptada"]
DEFAULT_STATUS = STATUSES[0]
DESCRIPTION_CHARS = 300
EDITABLE_FIELDS = ("status", "notes")


def from_offer(offer: Dict[str, Any], cv_label: str, today: Optional[date] = None) -> Application:
    """Crea una candidatura a partir de una oferta encontrada en «Buscar empleo»."""
    return {
        "cv_label": cv_label,
        "adzuna_id": offer["adzuna_id"],
        "company": offer["company"],
        "title": offer["title"],
        "location": offer.get("location", ""),
        "description": offer.get("description", "")[:DESCRIPTION_CHARS],
        "company_url": offer.get("company_url", ""),
        "offer_url": offer.get("offer_url", ""),
        "source": "Adzuna",
        "score": offer.get("score"),
        "status": DEFAULT_STATUS,
        "applied_at": (today or date.today()).isoformat(),
        "notes": "",
    }


def manual(company: str, title: str, offer_url: str = "", cv_label: str = "", notes: str = "",
           today: Optional[date] = None) -> Application:
    """Crea una candidatura añadida a mano por el usuario."""
    if not company.strip() or not title.strip():
        raise ValueError("Indica al menos la empresa y el puesto.")
    return {
        "cv_label": cv_label.strip() or "Sin CV indicado",
        "adzuna_id": None,
        "company": company.strip(),
        "title": title.strip(),
        "location": "",
        "description": "",
        "company_url": "",
        "offer_url": offer_url.strip(),
        "source": "Manual",
        "score": None,
        "status": DEFAULT_STATUS,
        "applied_at": (today or date.today()).isoformat(),
        "notes": notes.strip(),
    }


def changed_rows(original: pd.DataFrame, edited: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    """Compara la tabla original con la editada y devuelve, por id, los campos editables que cambiaron."""
    changes: Dict[str, Dict[str, str]] = {}
    for app_id in edited.index:
        new = {field: edited.at[app_id, field] or "" for field in EDITABLE_FIELDS}
        old = {field: original.at[app_id, field] or "" for field in EDITABLE_FIELDS}
        if new != old:
            changes[str(app_id)] = new
    return changes


def count_by_status(applications: list) -> Dict[str, int]:
    """Número de candidaturas en cada estado, en el orden del panel."""
    return {status: sum(1 for a in applications if a.get("status") == status) for status in STATUSES}
