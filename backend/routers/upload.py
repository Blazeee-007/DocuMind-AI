"""
Upload router — POST /upload
Validates file type (server-side magic bytes), parses document text,
creates a session, and returns doc_id + metadata.
"""
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.models.schemas import UploadResponse
from backend.services.file_parser import parse_document
from backend.services.storage_service import create_session
from backend.utils.helpers import clean_text, chunk_text, reading_time_minutes

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")) * 1024 * 1024

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/upload", response_model=UploadResponse, tags=["Upload"])
@limiter.limit("20/minute")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    Upload a document (PDF, DOCX, TXT, CSV).
    Returns a doc_id used for all subsequent analysis and chat endpoints.
    """
    # Read file bytes
    file_bytes = await file.read()

    # Size check
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_BYTES // (1024*1024)} MB.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Parse document (also validates type)
    try:
        parsed = parse_document(file_bytes, file.filename or "upload")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse document: {str(exc)}",
        )

    text = clean_text(parsed["text"])
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="Document appears to be empty or contains no extractable text.",
        )

    # Chunk text for later use
    chunks = chunk_text(text)

    # Create session
    doc_id = create_session(
        filename=file.filename or "upload",
        mime_type=parsed["mime_type"],
        text=text,
        chunks=chunks,
        word_count=parsed["word_count"],
        page_count=parsed["page_count"],
    )

    return UploadResponse(
        doc_id=doc_id,
        filename=file.filename or "upload",
        file_type=parsed["mime_type"],
        word_count=parsed["word_count"],
        page_count=parsed["page_count"],
        reading_time_minutes=reading_time_minutes(parsed["word_count"]),
        char_count=len(text),
    )
