"""Práctica de entrevistas y asistente conversacional."""

from __future__ import annotations

from typing import List

from talentlens import llm
from talentlens.llm import Message

INTERVIEW_SYSTEM_PROMPT = "Eres un entrenador de entrevistas laborales."
ASSISTANT_SYSTEM_PROMPT = "Eres un asistente experto en trabajo, CVs y desarrollo profesional."


def interview_questions(role: str) -> str:
    """Genera preguntas habituales de entrevista para un puesto."""
    return llm.ask(INTERVIEW_SYSTEM_PROMPT, f"Genera 5 preguntas comunes para el rol de {role}.")


def new_conversation() -> List[Message]:
    """Conversación inicial del asistente, solo con su mensaje de sistema."""
    return [{"role": "system", "content": ASSISTANT_SYSTEM_PROMPT}]


def reply(conversation: List[Message]) -> str:
    """Respuesta del asistente al último mensaje de la conversación."""
    return llm.chat(conversation)
