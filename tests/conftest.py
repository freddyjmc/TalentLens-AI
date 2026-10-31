"""Configuración común de los tests: sin red, sin claves reales y con una IA simulada."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

import openai
import pytest
import requests

from talentlens import config, llm

ENV_VARS = ("OPENAI_API_KEY", "OPENAI_MODEL", "MONGODB_URI", "MONGODB_DB_NAME", "ADZUNA_APP_ID", "ADZUNA_APP_KEY")


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    """Cada test empieza sin variables de entorno ni .env: nunca se leen las claves reales del desarrollador."""
    monkeypatch.setattr(config, "load_dotenv", lambda *args, **kwargs: None)
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Cualquier llamada real a OpenAI o a internet hace fallar el test."""
    def blocked(*args, **kwargs):
        raise AssertionError("Un test ha intentado una llamada de red real")

    monkeypatch.setattr(openai.ChatCompletion, "create", blocked)
    monkeypatch.setattr(requests, "get", blocked)


@pytest.fixture
def set_env(monkeypatch) -> Callable[..., None]:
    """Define variables de entorno para un test y recarga la configuración."""
    def _set(**values: str) -> None:
        for name, value in values.items():
            monkeypatch.setenv(name, value)
        config.get_settings.cache_clear()

    return _set


class FakeLLM:
    """Sustituye a talentlens.llm: guarda las peticiones y devuelve respuestas preparadas."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.text_response = "respuesta simulada"
        self.json_response: Any = {}

    def ask(self, system: str, prompt: str, **options: Any) -> str:
        self.calls.append({"system": system, "prompt": prompt, **options})
        return self.text_response

    def ask_json(self, system: str, prompt: str, **options: Any) -> Dict[str, Any]:
        self.calls.append({"system": system, "prompt": prompt, **options})
        response = self.json_response(prompt) if callable(self.json_response) else self.json_response
        return json.loads(json.dumps(response))  # copia, como si viniera de la API

    def chat(self, messages, **options: Any) -> str:
        self.calls.append({"messages": list(messages), **options})
        return self.text_response


@pytest.fixture
def fake_llm(monkeypatch) -> FakeLLM:
    fake = FakeLLM()
    monkeypatch.setattr(llm, "ask", fake.ask)
    monkeypatch.setattr(llm, "ask_json", fake.ask_json)
    monkeypatch.setattr(llm, "chat", fake.chat)
    return fake


class FakeResponse:
    """Respuesta HTTP mínima para simular `requests.get`."""

    def __init__(self, status_code: int = 200, json_data: Optional[Any] = None, content: bytes = b""):
        self.status_code = status_code
        self._json = json_data
        self.content = content
        self.text = content.decode("utf-8", "replace")

    def json(self) -> Any:
        if self._json is None:
            raise ValueError("sin JSON")
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error")
