"""
Analyze router — POST /analyze/{doc_id}, POST /extract/{doc_id}
Delegates to AI service for summarization and data extraction.
"""
import json
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.models.schemas import AnalyzeResponse, ExtractResponse
from backend.services import storage_service
from backend.services.ai_service import summarize_document, extract_data

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/analyze/{doc_id}", response_model=AnalyzeResponse, tags=["Analysis"])
@limiter.limit("10/minute")
async def analyze_document(doc_id: str, request: Request):
    """
    Generate a structured AI summary of the uploaded document.
    Uses map-reduce for multi-chunk documents.
    Results are cached per session.
    """
    session = storage_service.get_session(doc_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Document session not found. Please upload again.")

    # Return cached summary if available
    cached = storage_service.get_cached_summary(doc_id)
    if cached:
        data = json.loads(cached)
        return AnalyzeResponse(
            doc_id=doc_id,
            word_count=session["word_count"],
            **data,
        )

    try:
        result = summarize_document(session["text"])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(exc)}")

    # Cache the result
    cache_payload = {
        "executive_summary": result["executive_summary"],
        "key_points": result["key_points"],
        "main_topics": result["main_topics"],
        "tone": result["tone"],
        "model_used": result["model_used"],
    }
    storage_service.cache_summary(doc_id, json.dumps(cache_payload))

    return AnalyzeResponse(
        doc_id=doc_id,
        word_count=session["word_count"],
        **cache_payload,
    )


@router.post("/extract/{doc_id}", response_model=ExtractResponse, tags=["Analysis"])
@limiter.limit("10/minute")
async def extract_document_data(doc_id: str, request: Request):
    """
    Extract structured data from the document: entities, key facts, tables, and lists.
    """
    session = storage_service.get_session(doc_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Document session not found. Please upload again.")

    try:
        result = extract_data(session["text"])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(exc)}")

    return ExtractResponse(
        doc_id=doc_id,
        entities=result.get("entities", []),
        key_facts=result.get("key_facts", []),
        tables=result.get("tables", []),
        lists=result.get("lists", []),
        model_used=result["model_used"],
    )
