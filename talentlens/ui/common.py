"""Utilidades compartidas por las páginas de la interfaz."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st

from talentlens.db import DBManager
from talentlens.files import read_text

DB_UNAVAILABLE = "No se pudo acceder a la base de datos. ¿Está MongoDB en marcha?"


@st.cache_resource
def get_db() -> DBManager:
    """Una sola conexión a MongoDB para toda la aplicación."""
    return DBManager.from_settings()


def save(db: DBManager, collection: str, data: Dict[str, Any], success_message: str) -> bool:
    """Guarda en MongoDB y muestra un mensaje claro si la base de datos no responde."""
    try:
        db.save_data(collection, data)
    except Exception as e:
        st.error(f"{DB_UNAVAILABLE} ({e})")
        return False
    st.success(success_message)
    return True


def fetch(db: DBManager, collection: str, query: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
    """Lee de MongoDB. Devuelve None (y avisa) si la base de datos no responde."""
    try:
        return db.fetch_data(collection, query)
    except Exception as e:
        st.error(f"{DB_UNAVAILABLE} ({e})")
        return None


def file_key(uploaded_file) -> str:
    """Identifica un archivo subido para no repetir el análisis en cada recarga."""
    return f"{uploaded_file.name}-{uploaded_file.size}"


def read_uploaded(uploaded_file) -> str:
    """Texto de un archivo subido con `st.file_uploader`."""
    return read_text(uploaded_file.name, uploaded_file.getvalue())
