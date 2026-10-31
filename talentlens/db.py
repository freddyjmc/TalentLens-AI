"""Acceso a MongoDB."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pymongo import MongoClient

from talentlens.config import get_settings

# Colecciones que usa la aplicación
JOB_OFFERS = "job_offers"
CV_REVIEWS = "cv_reviews"
ATS_CVS = "ats_cvs"
APPLICATIONS = "applications"

Document = Dict[str, Any]


class DBManager:
    def __init__(self, uri: str, db_name: str, client: Optional[MongoClient] = None):
        # Fallar en 5 s (en vez de 30) si MongoDB no está en marcha
        self.client = client or MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]

    @classmethod
    def from_settings(cls) -> DBManager:
        """Crea la conexión con la configuración del .env."""
        settings = get_settings()
        if not settings.mongodb_uri or not settings.mongodb_db_name:
            raise ValueError("MONGODB_URI o MONGODB_DB_NAME no están configurados en el archivo .env.")
        return cls(settings.mongodb_uri, settings.mongodb_db_name)

    def save_data(self, collection_name: str, data: Document) -> None:
        """Guarda un documento en una colección."""
        self.db[collection_name].insert_one(data)

    def fetch_data(self, collection_name: str, query: Optional[Document] = None) -> List[Document]:
        """Obtiene los documentos de una colección que cumplen la consulta."""
        return list(self.db[collection_name].find(query or {}))

    def update_data(self, collection_name: str, query: Document, values: Document) -> None:
        """Actualiza los campos indicados del primer documento que cumpla la consulta."""
        self.db[collection_name].update_one(query, {"$set": values})

    def delete_data(self, collection_name: str, query: Document) -> None:
        """Elimina los documentos que cumplen la consulta."""
        self.db[collection_name].delete_many(query)
