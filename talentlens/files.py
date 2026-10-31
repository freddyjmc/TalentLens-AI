"""Lectura del texto de los archivos que sube el usuario."""

from __future__ import annotations

import io

from docx import Document
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = ("txt", "pdf", "docx")


def read_text(filename: str, data: bytes) -> str:
    """Devuelve el texto de un archivo .txt, .pdf o .docx a partir de su contenido."""
    name = filename.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        return "\n".join(paragraph.text for paragraph in Document(io.BytesIO(data)).paragraphs)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")
