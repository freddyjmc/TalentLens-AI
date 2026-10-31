from talentlens import assistant


def test_new_conversation_only_has_the_system_message():
    assert assistant.new_conversation() == [{"role": "system", "content": assistant.ASSISTANT_SYSTEM_PROMPT}]


def test_reply_sends_the_whole_conversation(fake_llm):
    conversation = assistant.new_conversation() + [{"role": "user", "content": "¿Cómo mejoro mi CV?"}]
    assert assistant.reply(conversation) == "respuesta simulada"
    assert fake_llm.calls[0]["messages"] == conversation


def test_interview_questions_include_the_role(fake_llm):
    assistant.interview_questions("Contable")
    assert "Contable" in fake_llm.calls[0]["prompt"]
