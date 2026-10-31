"""Exportación del CV (en el formato Markdown sencillo que genera la IA) a TXT, Word y PDF."""

from __future__ import annotations

import io
from typing import List, Tuple

from docx import Document
from fpdf import FPDF

Line = Tuple[str, str]  # (tipo, texto): name, heading, subheading, bullet o text

# Caracteres habituales en textos de la IA que las fuentes básicas del PDF no tienen
PDF_REPLACEMENTS = {
    "–": "-", "—": "-", "•": "-", "’": "'", "‘": "'",
    "“": '"', "”": '"', "…": "...", "€": "EUR", " ": " ",
}
# Estilo de cada tipo de línea en el PDF: (estilo de fuente, tamaño, alto de línea)
PDF_STYLES = {
    "name": ("B", 18, 10), "heading": ("B", 13, 8), "subheading": ("B", 11, 6),
    "bullet": ("", 10, 5), "text": ("", 10, 5),
}
# Escalas que se prueban para que el CV quepa en una página sin quedar ilegible
PDF_FIT_SCALES = (1.0, 0.92, 0.85)
PDF_MARGIN_MM = 15


def parse_cv(cv_markdown: str) -> List[Line]:
    """Convierte el CV en una lista de líneas con su tipo."""
    lines: List[Line] = []
    for raw in cv_markdown.splitlines():
        line = raw.strip().replace("**", "")
        if not line:
            continue
        if line.startswith("### "):
            lines.append(("subheading", line[4:]))
        elif line.startswith("## "):
            lines.append(("heading", line[3:]))
        elif line.startswith("# "):
            lines.append(("name", line[2:]))
        elif line.startswith(("- ", "* ")):
            lines.append(("bullet", line[2:]))
        else:
            lines.append(("text", line))
    return lines


def to_txt(cv_markdown: str) -> bytes:
    """Texto plano, el formato más seguro para pegar en portales de empleo."""
    out: List[str] = []
    for kind, text in parse_cv(cv_markdown):
        if kind in ("name", "heading"):
            if out:
                out.append("")
            out.append(text.upper())
        elif kind == "bullet":
            out.append(f"- {text}")
        else:
            out.append(text)
    return "\n".join(out).encode("utf-8")


def to_docx(cv_markdown: str) -> bytes:
    """Documento de Word con estilos estándar (títulos y viñetas) que los ATS leen bien."""
    doc = Document()
    for kind, text in parse_cv(cv_markdown):
        if kind == "name":
            doc.add_heading(text, level=0)
        elif kind == "heading":
            doc.add_heading(text, level=1)
        elif kind == "subheading":
            doc.add_heading(text, level=2)
        elif kind == "bullet":
            doc.add_paragraph(text, style="List Bullet")
        else:
            doc.add_paragraph(text)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _pdf_safe(text: str) -> str:
    """Adapta el texto a las fuentes básicas del PDF (latin-1)."""
    for char, replacement in PDF_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    return text.encode("latin-1", "replace").decode("latin-1")


def _render_pdf(lines: List[Line], scale: float) -> FPDF:
    """Dibuja el CV con letra, interlineado y márgenes proporcionales a `scale`."""
    margin = PDF_MARGIN_MM * scale
    pdf = FPDF()
    pdf.set_margins(margin, margin, margin)
    pdf.set_auto_page_break(auto=True, margin=margin)
    pdf.add_page()
    for kind, text in lines:
        style, size, height = PDF_STYLES[kind]
        if kind == "heading":
            pdf.ln(3 * scale)
        pdf.set_font("Helvetica", style, size * scale)
        if kind == "bullet":
            text = f"-  {text}"
        pdf.multi_cell(0, height * scale, _pdf_safe(text), new_x="LMARGIN", new_y="NEXT")
    return pdf


def to_pdf(cv_markdown: str) -> bytes:
    """PDF de una columna con texto seleccionable.

    Si el CV se pasa por poco de una página, se reduce un poco la escala para que quepa
    y no quede una segunda página casi vacía.
    """
    lines = parse_cv(cv_markdown)
    for scale in PDF_FIT_SCALES:
        pdf = _render_pdf(lines, scale)
        if pdf.page_no() == 1:
            break
    else:
        # No cabe en una página ni reduciendo: se usa el tamaño normal
        pdf = _render_pdf(lines, 1.0)
    return bytes(pdf.output())
