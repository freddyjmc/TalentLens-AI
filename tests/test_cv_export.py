import io

import pytest
from docx import Document
from pypdf import PdfReader

from talentlens.cv.export import _render_pdf, parse_cv, to_docx, to_pdf, to_txt

SAMPLE_CV = """# Ana Pérez
ana@example.com | Madrid

## Experiencia
### Analista de datos - Empresa S.L. (2022 - 2024)
- Informes con **Power BI**
* Consultas SQL
"""


def _pdf_pages(data: bytes) -> int:
    return len(PdfReader(io.BytesIO(data)).pages)


def test_parse_cv_classifies_each_line_and_removes_bold_markers():
    assert parse_cv(SAMPLE_CV) == [
        ("name", "Ana Pérez"),
        ("text", "ana@example.com | Madrid"),
        ("heading", "Experiencia"),
        ("subheading", "Analista de datos - Empresa S.L. (2022 - 2024)"),
        ("bullet", "Informes con Power BI"),
        ("bullet", "Consultas SQL"),
    ]


def test_txt_uses_uppercase_titles_and_blank_line_between_sections():
    lines = to_txt(SAMPLE_CV).decode("utf-8").splitlines()
    assert lines[0] == "ANA PÉREZ"
    assert lines[2:4] == ["", "EXPERIENCIA"]
    assert "- Consultas SQL" in lines


def test_docx_uses_standard_heading_and_bullet_styles():
    paragraphs = Document(io.BytesIO(to_docx(SAMPLE_CV))).paragraphs
    styles = {p.text: p.style.name for p in paragraphs}
    assert styles["Ana Pérez"] == "Title"
    assert styles["Experiencia"] == "Heading 1"
    assert styles["Analista de datos - Empresa S.L. (2022 - 2024)"] == "Heading 2"
    assert styles["Consultas SQL"] == "List Bullet"


def test_pdf_has_selectable_text_and_replaces_unsupported_characters():
    text = PdfReader(io.BytesIO(to_pdf("# Ana\n- Salario “alto” – 1.000 € • remoto\n"))).pages[0].extract_text()
    assert 'Salario "alto" - 1.000 EUR - remoto' in text


def _cv_with_bullets(count: int) -> str:
    return "# Nombre\n## Experiencia\n" + "".join(f"- Logro número {i} descrito con detalle\n" for i in range(count))


def test_pdf_shrinks_slightly_to_avoid_an_almost_empty_second_page():
    # Buscar un CV que a tamaño normal se pase justo a una segunda página
    count = next(n for n in range(30, 80) if _render_pdf(parse_cv(_cv_with_bullets(n)), 1.0).page_no() == 2)
    data = to_pdf(_cv_with_bullets(count))
    assert _pdf_pages(data) == 1
    text = PdfReader(io.BytesIO(data)).pages[0].extract_text()
    assert f"Logro número {count - 1} " in text  # no se ha perdido contenido


@pytest.mark.parametrize("bullets", [150])
def test_pdf_keeps_normal_size_when_content_does_not_fit_in_one_page(bullets):
    assert _pdf_pages(to_pdf(_cv_with_bullets(bullets))) >= 2
