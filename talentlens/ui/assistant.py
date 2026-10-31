"""Página «Asistente Inteligente»: chat sobre empleo, CVs y desarrollo profesional."""

import streamlit as st

from talentlens import assistant
from talentlens.db import DBManager


def render(db: DBManager) -> None:
    st.header("Asistente Inteligente")
    if "messages" not in st.session_state:
        st.session_state["messages"] = assistant.new_conversation()
    messages = st.session_state["messages"]

    # Mostrar el historial sin el mensaje de sistema
    for message in messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.write(message["content"])

    user_input = (st.chat_input("Escribe tu pregunta o solicitud") or "").strip()
    if not user_input:
        return

    messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    try:
        answer = assistant.reply(messages)
    except Exception as e:
        # Quitar la pregunta sin respuesta para no reenviarla en la siguiente llamada
        messages.pop()
        st.error(f"Error al procesar la solicitud: {e}")
        return
    messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.write(answer)
