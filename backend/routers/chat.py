"""
Chat router — POST /chat/{doc_id}, GET /history/{doc_id}, DELETE /session/{doc_id}
RAG-powered Q&A with conversation history tracking.
"""
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.models.schemas import ChatRequest, ChatResponse, HistoryResponse, ChatMessage
from backend.services import storage_service
from backend.services.ai_service import answer_question, embed_chunks

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/chat/{doc_id}", response_model=ChatResponse, tags=["Chat"])
@limiter.limit("30/minute")
async def chat_with_document(doc_id: str, body: ChatRequest, request: Request):
    """
    Answer a question grounded in the uploaded document using RAG + AI.
    Conversation history is maintained per session.
    """
    session = storage_service.get_session(doc_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Document session not found. Please upload again.")

    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if len(question) > 1000:
        raise HTTPException(status_code=400, detail="Question too long (max 1000 characters).")

    # Lazy-compute embeddings on first Q&A request
    embeddings = storage_service.get_embeddings(doc_id)
    if embeddings is None:
        embeddings = embed_chunks(session["chunks"])
        storage_service.set_embeddings(doc_id, embeddings)

    try:
        result = answer_question(
            question=question,
            chunks=session["chunks"],
            embeddings=embeddings,
            history=storage_service.get_history(doc_id),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(exc)}")

    # Store updated embeddings if freshly computed
    if storage_service.get_embeddings(doc_id) is None:
        storage_service.set_embeddings(doc_id, result["embeddings"])

    # Persist conversation turn
    storage_service.add_chat_message(doc_id, "user", question)
    storage_service.add_chat_message(doc_id, "assistant", result["answer"])

    return ChatResponse(
        doc_id=doc_id,
        question=question,
        answer=result["answer"],
        sources=result["sources"],
        model_used=result["model_used"],
    )


@router.get("/history/{doc_id}", response_model=HistoryResponse, tags=["Chat"])
async def get_history(doc_id: str):
    """Return the full conversation history for a document session."""
    session = storage_service.get_session(doc_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Document session not found.")

    messages = [
        ChatMessage(role=m["role"], content=m["content"], timestamp=m["timestamp"])
        for m in storage_service.get_history(doc_id)
    ]

    return HistoryResponse(
        doc_id=doc_id,
        messages=messages,
        total_messages=len(messages),
    )


@router.delete("/session/{doc_id}", tags=["Chat"])
async def delete_session(doc_id: str):
    """Delete a document session and all associated data."""
    deleted = storage_service.delete_session(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"message": "Session deleted successfully.", "doc_id": doc_id}
