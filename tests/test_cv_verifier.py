from talentlens.cv.export import to_pdf
from talentlens.cv.verifier import check_rules, check_with_ai

ORIGINAL = """Ana Pérez
ana@example.com | +34 600 123 456 | Madrid
Analista de datos (2019 - 2023)
Inglés: básico (A2)"""

GOOD_CV = """# Ana Pérez
ana@example.com | +34 600 123 456 | Madrid
## Experiencia
### Analista de datos (2019 - 2023)
## Idiomas
- Inglés: básico (A2)"""


def _failed(checks):
    return [check.message for check in checks if not check.ok]


def test_correct_cv_passes_every_rule():
    checks = check_rules(ORIGINAL, GOOD_CV, to_pdf(GOOD_CV))
    assert _failed(checks) == []
    assert any("Teléfono +34 600 123 456: conservado" in check.message for check in checks)


def test_year_ranges_are_not_treated_as_phone_numbers():
    messages = [check.message for check in check_rules(ORIGINAL, GOOD_CV, to_pdf(GOOD_CV))]
    assert not any("2019 - 2023" in message for message in messages)


def test_detects_lost_contact_data_and_language_level():
    bad_cv = GOOD_CV.replace("ana@example.com", "").replace("600 123 456", "").replace("(A2)", "")
    failed = _failed(check_rules(ORIGINAL, bad_cv, to_pdf(bad_cv)))
    assert "Email ana@example.com: no aparece en el CV generado." in failed
    assert "Teléfono +34 600 123 456: no aparece en el CV generado." in failed
    assert "Nivel de idioma A2: no aparece en el CV generado." in failed


def test_counts_pending_fields():
    cv = GOOD_CV + "\n[COMPLETAR: empresa]\n[COMPLETAR: fechas]"
    assert "Campos por completar: 2." in _failed(check_rules(ORIGINAL, cv, to_pdf(cv)))


def test_ai_check_returns_the_three_lists_even_if_the_model_omits_some(fake_llm):
    fake_llm.json_response = {"inventado": ["Lideró un equipo de 12 personas"], "otra": ["ignorada"]}
    assert check_with_ai(ORIGINAL, GOOD_CV) == {
        "inventado": ["Lideró un equipo de 12 personas"],
        "perdido": [],
        "estilo": [],
    }
    call = fake_llm.calls[0]
    assert call["temperature"] == 0
    assert "CV ORIGINAL:\n" + ORIGINAL in call["prompt"] and "CV GENERADO:\n" + GOOD_CV in call["prompt"]
