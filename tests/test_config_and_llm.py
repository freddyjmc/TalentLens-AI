import openai
import pytest

from talentlens import llm
from talentlens.config import DEFAULT_MAX_TOKENS, DEFAULT_OPENAI_MODEL, get_settings


def test_settings_use_defaults_when_env_is_empty():
    settings = get_settings()
    assert settings.openai_api_key is None
    assert settings.openai_model == DEFAULT_OPENAI_MODEL
    assert settings.openai_max_tokens == DEFAULT_MAX_TOKENS


def test_settings_read_and_strip_env_values(set_env):
    set_env(OPENAI_API_KEY="  sk-test  ", OPENAI_MODEL="gpt-4.1-mini", ADZUNA_APP_ID="abc", ADZUNA_APP_KEY=" ")
    settings = get_settings()
    assert settings.openai_api_key == "sk-test"
    assert settings.openai_model == "gpt-4.1-mini"
    assert settings.adzuna_app_id == "abc"
    assert settings.adzuna_app_key is None  # un valor en blanco cuenta como no configurado


def test_chat_without_api_key_fails_with_clear_message():
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        llm.chat([{"role": "user", "content": "hola"}])


def test_chat_sends_model_limits_and_json_mode(set_env, monkeypatch):
    set_env(OPENAI_API_KEY="sk-test")
    sent = {}

    def fake_create(**params):
        sent.update(params)
        return {"choices": [{"message": {"content": '  {"ok": true}  '}}]}

    monkeypatch.setattr(openai.ChatCompletion, "create", fake_create)

    assert llm.ask_json("sistema", "pregunta", temperature=0) == {"ok": True}
    assert sent["model"] == DEFAULT_OPENAI_MODEL
    assert sent["max_tokens"] == DEFAULT_MAX_TOKENS
    assert sent["temperature"] == 0
    assert sent["response_format"] == {"type": "json_object"}
    assert sent["messages"] == [{"role": "system", "content": "sistema"}, {"role": "user", "content": "pregunta"}]


def test_chat_omits_optional_params_and_strips_text(set_env, monkeypatch):
    set_env(OPENAI_API_KEY="sk-test")
    sent = {}

    def fake_create(**params):
        sent.update(params)
        return {"choices": [{"message": {"content": "\n respuesta \n"}}]}

    monkeypatch.setattr(openai.ChatCompletion, "create", fake_create)

    assert llm.ask("sistema", "pregunta", max_tokens=50) == "respuesta"
    assert sent["max_tokens"] == 50
    assert "temperature" not in sent and "response_format" not in sent
