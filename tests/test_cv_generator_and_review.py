from talentlens.cv.generator import ATS_INSTRUCTIONS, build_prompt, generate_ats_cv
from talentlens.cv.review import review_cv


def test_prompt_includes_rules_cv_and_optional_target_role():
    prompt = build_prompt("CV de Ana", "  Data Analyst ")
    assert prompt.startswith(ATS_INSTRUCTIONS)
    assert "CV original:\nCV de Ana" in prompt
    assert "Puesto objetivo: Data Analyst." in prompt


def test_prompt_without_target_role_does_not_mention_it():
    assert "Puesto objetivo" not in build_prompt("CV de Ana", "   ")


def test_generation_rules_forbid_inventing_data():
    assert "No inventes nada" in ATS_INSTRUCTIONS
    assert "[COMPLETAR" in ATS_INSTRUCTIONS


def test_generate_uses_low_temperature_and_double_token_limit(fake_llm):
    fake_llm.text_response = "# Ana"
    assert generate_ats_cv("CV de Ana") == "# Ana"
    call = fake_llm.calls[0]
    assert call["temperature"] == 0.2
    assert call["max_tokens"] == 2000


def test_review_sends_cv_to_the_model(fake_llm):
    assert review_cv("CV de Ana") == "respuesta simulada"
    assert "CV de Ana" in fake_llm.calls[0]["prompt"]
