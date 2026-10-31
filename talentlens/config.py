"""Configuración de la aplicación a partir de variables de entorno (o del archivo .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"  # gpt-3.5-turbo está retirado
DEFAULT_MAX_TOKENS = 1000  # con menos, las respuestas largas se cortaban


@dataclass(frozen=True)
class Settings:
    openai_api_key: Optional[str]
    openai_model: str
    openai_max_tokens: int
    mongodb_uri: Optional[str]
    mongodb_db_name: Optional[str]
    adzuna_app_id: Optional[str]
    adzuna_app_key: Optional[str]


def _env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Lee la configuración una sola vez. Las variables del sistema tienen prioridad sobre el .env."""
    load_dotenv()
    return Settings(
        openai_api_key=_env("OPENAI_API_KEY"),
        openai_model=_env("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL,
        openai_max_tokens=DEFAULT_MAX_TOKENS,
        mongodb_uri=_env("MONGODB_URI"),
        mongodb_db_name=_env("MONGODB_DB_NAME"),
        adzuna_app_id=_env("ADZUNA_APP_ID"),
        adzuna_app_key=_env("ADZUNA_APP_KEY"),
    )
