from talentlens.cv.export import to_docx, to_pdf
from talentlens.files import read_text


def test_reads_utf8_text():
    assert read_text("cv.txt", "Málaga".encode()) == "Málaga"


def test_falls_back_to_latin1_for_non_utf8_text():
    assert read_text("cv.txt", "Málaga".encode("latin-1")) == "Málaga"


def test_reads_pdf_text():
    data = to_pdf("# Ana Pérez\n## Habilidades\n- Python y SQL\n")
    text = read_text("CV.PDF", data)  # la extensión no distingue mayúsculas
    assert "Ana" in text and "Python y SQL" in text


def test_reads_docx_paragraphs():
    data = to_docx("# Ana Pérez\n## Habilidades\n- Python y SQL\n")
    assert read_text("cv.docx", data).splitlines() == ["Ana Pérez", "Habilidades", "Python y SQL"]
