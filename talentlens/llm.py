"""Acceso centralizado a la API de OpenAI.

Todas las funciones de IA pasan por aquí: así el modelo y los límites se configuran en un solo sitio
y los tests pueden sustituir estas funciones sin hacer llamadas reales.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import openai

from talentlens.config import get_settings

Message = Dict[str, str]


def chat(
    messages: List[Message],
    *,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    json_mode: bool = False,
) -> str:
    """Envía una conversación al modelo y devuelve el texto de la respuesta."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY no está configurada en el archivo .env.")
    openai.api_key = settings.openai_api_key

    params: Dict[str, Any] = {
        "model": settings.openai_model,
        "messages": messages,
        "max_tokens": max_tokens or settings.openai_max_tokens,
    }
    if temperature is not None:
        params["temperature"] = temperature
    if json_mode:
        params["response_format"] = {"type": "json_object"}
    response = openai.ChatCompletion.create(**params)
    return response["choices"][0]["message"]["content"].strip()


def ask(system: str, prompt: str, **options: Any) -> str:
    """Atajo para una pregunta con un mensaje de sistema y uno de usuario."""
    return chat([{"role": "system", "content": system}, {"role": "user", "content": prompt}], **options)


def ask_json(system: str, prompt: str, **options: Any) -> Dict[str, Any]:
    """Como `ask`, pero obliga al modelo a responder con un objeto JSON y lo devuelve ya convertido."""
    return json.loads(ask(system, prompt, json_mode=True, **options))
