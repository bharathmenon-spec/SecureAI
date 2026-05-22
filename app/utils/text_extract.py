"""Local text extraction for supported document formats."""
import json
import re
from io import BytesIO
from typing import Union

from app.core.logger import get_logger

logger = get_logger(__name__)

_EXT_MAP = {
    "pdf": "pdf",
    "docx": "docx",
    "doc": "docx",
    "txt": "txt",
    "text": "txt",
    "html": "html",
    "htm": "html",
    "json": "json",
}


def detect_source_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _EXT_MAP.get(ext, "txt")


def clean_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph breaks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_docx(data: bytes) -> str:
    import docx

    document = docx.Document(BytesIO(data))
    return "\n".join(p.text for p in document.paragraphs)


def _extract_html(data: bytes) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(data, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n")


def _flatten_json(value, parts: list) -> None:
    if isinstance(value, dict):
        for key, sub in value.items():
            parts.append(str(key))
            _flatten_json(sub, parts)
    elif isinstance(value, list):
        for sub in value:
            _flatten_json(sub, parts)
    else:
        parts.append(str(value))


def _extract_json(data: bytes) -> str:
    try:
        parsed = json.loads(data.decode("utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return data.decode("utf-8", errors="ignore")
    parts: list = []
    _flatten_json(parsed, parts)
    return "\n".join(parts)


def extract_text(data: Union[bytes, str], source_type: str, filename: str = "") -> str:
    """Extract plain text from raw document bytes (or a raw string)."""
    if isinstance(data, str):
        raw = data if source_type in ("txt", "text", "") else data.encode("utf-8")
        if isinstance(raw, str):
            return clean_text(raw)
        data = raw

    source_type = (source_type or "txt").lower()
    try:
        if source_type == "pdf":
            text = _extract_pdf(data)
        elif source_type == "docx":
            text = _extract_docx(data)
        elif source_type == "html":
            text = _extract_html(data)
        elif source_type == "json":
            text = _extract_json(data)
        else:
            text = data.decode("utf-8", errors="ignore")
    except Exception as exc:
        logger.warning("Extraction failed for %s (%s); falling back to raw decode",
                        filename, exc)
        text = data.decode("utf-8", errors="ignore")
    return clean_text(text)
