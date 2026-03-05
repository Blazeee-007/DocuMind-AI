"""
File parser service — extracts raw text and metadata from uploaded documents.
Supports: PDF (pdfplumber), DOCX (python-docx), CSV (pandas), TXT (native).
"""
import io
from typing import Dict, Any

# PDF
import pdfplumber

# DOCX
from docx import Document as DocxDocument

# CSV
import pandas as pd


def parse_pdf(file_bytes: bytes) -> Dict[str, Any]:
    """Extract text from a PDF file."""
    text_parts = []
    page_count = 0

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    full_text = "\n\n".join(text_parts)
    word_count = len(full_text.split())

    return {
        "text": full_text,
        "page_count": page_count,
        "word_count": word_count,
    }


def parse_docx(file_bytes: bytes) -> Dict[str, Any]:
    """Extract text from a DOCX file."""
    doc = DocxDocument(io.BytesIO(file_bytes))
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    full_text = "\n\n".join(paragraphs)

    # Count approximate pages (250 words/page)
    word_count = len(full_text.split())
    page_count = max(1, word_count // 250)

    return {
        "text": full_text,
        "page_count": page_count,
        "word_count": word_count,
    }


def parse_csv(file_bytes: bytes) -> Dict[str, Any]:
    """Convert CSV to a readable text representation."""
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception:
        # Fallback to default encoding
        df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")

    # Build a human-readable text block
    lines = []
    lines.append(f"CSV File — {len(df)} rows × {len(df.columns)} columns")
    lines.append(f"Columns: {', '.join(str(c) for c in df.columns)}")
    lines.append("")
    # Include full data as pipe-separated text (truncated to 5000 rows for safety)
    lines.append(df.head(5000).to_string(index=False))

    full_text = "\n".join(lines)
    word_count = len(full_text.split())

    return {
        "text": full_text,
        "page_count": 1,
        "word_count": word_count,
        "dataframe": df,  # Kept for structured extraction
    }


def parse_txt(file_bytes: bytes) -> Dict[str, Any]:
    """Extract text from a plain-text file."""
    try:
        full_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        full_text = file_bytes.decode("latin-1", errors="replace")

    word_count = len(full_text.split())
    page_count = max(1, word_count // 250)

    return {
        "text": full_text,
        "page_count": page_count,
        "word_count": word_count,
    }


# Mapping of MIME types / extensions to parsers
SUPPORTED_TYPES = {
    "application/pdf": parse_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": parse_docx,
    "text/csv": parse_csv,
    "text/plain": parse_txt,
}

EXTENSION_MAP = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".csv": "text/csv",
    ".txt": "text/plain",
}

# Magic byte signatures for server-side type validation
MAGIC_BYTES = {
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def detect_mime_type(file_bytes: bytes, filename: str) -> str:
    """
    Detect MIME type by magic bytes first, then fall back to extension.
    Raises ValueError for unsupported or mismatched types.
    """
    # Check magic bytes
    for magic, mime in MAGIC_BYTES.items():
        if file_bytes.startswith(magic):
            return mime

    # Fall back to extension
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext in EXTENSION_MAP:
        mime = EXTENSION_MAP[ext]
        # For CSV/TXT we can't validate magic bytes, trust extension
        if mime in ("text/csv", "text/plain"):
            # Quick sanity check — should be decodable as text
            try:
                file_bytes[:1024].decode("utf-8")
            except UnicodeDecodeError:
                try:
                    file_bytes[:1024].decode("latin-1")
                except Exception:
                    raise ValueError("File does not appear to be a valid text file.")
        return mime

    raise ValueError(
        f"Unsupported file type '{ext}'. Allowed: PDF, DOCX, TXT, CSV."
    )


def parse_document(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Detect file type, validate, and parse the document.
    Returns dict with keys: text, page_count, word_count, mime_type.
    """
    mime_type = detect_mime_type(file_bytes, filename)
    parser = SUPPORTED_TYPES.get(mime_type)
    if parser is None:
        raise ValueError(f"No parser available for MIME type '{mime_type}'.")

    result = parser(file_bytes)
    result["mime_type"] = mime_type
    # Remove non-serialisable dataframe (only needed internally)
    result.pop("dataframe", None)
    return result
