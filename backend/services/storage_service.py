"""
In-memory session store for uploaded documents.
Each session keyed by doc_id holds the parsed text, chunks,
embeddings, metadata, and conversation history.
Sessions are automatically purged after SESSION_TTL_HOURS.
"""
import asyncio
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np

SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "1"))

# ---------------------------------------------------------------------------
# Session schema (plain dict for speed — no extra dependencies)
# ---------------------------------------------------------------------------
# {
#   doc_id: {
#     "filename": str,
#     "mime_type": str,
#     "text": str,
#     "chunks": List[str],
#     "embeddings": List[np.ndarray] | None,
#     "word_count": int,
#     "page_count": int,
#     "char_count": int,
#     "created_at": datetime,
#     "history": List[{"role": str, "content": str, "timestamp": str}],
#     "summary_cache": str | None,
#   }
# }

_sessions: Dict[str, Dict[str, Any]] = {}
_cleanup_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

async def _cleanup_loop() -> None:
    """Periodically removes expired sessions."""
    while True:
        await asyncio.sleep(300)  # check every 5 minutes
        _evict_expired()


def _evict_expired() -> None:
    cutoff = datetime.utcnow() - timedelta(hours=SESSION_TTL_HOURS)
    expired = [k for k, v in _sessions.items() if v["created_at"] < cutoff]
    for k in expired:
        del _sessions[k]


def start_cleanup_task() -> None:
    """Call this on FastAPI startup."""
    global _cleanup_task
    loop = asyncio.get_event_loop()
    _cleanup_task = loop.create_task(_cleanup_loop())


def stop_cleanup_task() -> None:
    """Call this on FastAPI shutdown."""
    if _cleanup_task:
        _cleanup_task.cancel()


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def create_session(
    filename: str,
    mime_type: str,
    text: str,
    chunks: List[str],
    word_count: int,
    page_count: int,
) -> str:
    """Create a new session and return its doc_id."""
    doc_id = str(uuid.uuid4())
    _sessions[doc_id] = {
        "filename": filename,
        "mime_type": mime_type,
        "text": text,
        "chunks": chunks,
        "embeddings": None,   # lazy-loaded on first Q&A
        "word_count": word_count,
        "page_count": page_count,
        "char_count": len(text),
        "created_at": datetime.utcnow(),
        "history": [],
        "summary_cache": None,
    }
    return doc_id


def get_session(doc_id: str) -> Optional[Dict[str, Any]]:
    """Return session data or None if not found / expired."""
    session = _sessions.get(doc_id)
    if session is None:
        return None
    # Check TTL
    cutoff = datetime.utcnow() - timedelta(hours=SESSION_TTL_HOURS)
    if session["created_at"] < cutoff:
        del _sessions[doc_id]
        return None
    return session


def delete_session(doc_id: str) -> bool:
    """Delete a session. Returns True if it existed."""
    if doc_id in _sessions:
        del _sessions[doc_id]
        return True
    return False


def add_chat_message(doc_id: str, role: str, content: str) -> None:
    """Append a chat message to the session's history."""
    session = _sessions.get(doc_id)
    if session is None:
        return
    session["history"].append(
        {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


def get_history(doc_id: str) -> List[Dict[str, str]]:
    """Return the conversation history for a session."""
    session = _sessions.get(doc_id)
    if session is None:
        return []
    return session["history"]


def set_embeddings(doc_id: str, embeddings: List[np.ndarray]) -> None:
    """Store precomputed chunk embeddings."""
    session = _sessions.get(doc_id)
    if session:
        session["embeddings"] = embeddings


def get_embeddings(doc_id: str) -> Optional[List[np.ndarray]]:
    """Retrieve stored chunk embeddings."""
    session = _sessions.get(doc_id)
    if session is None:
        return None
    return session.get("embeddings")


def cache_summary(doc_id: str, summary_json: str) -> None:
    session = _sessions.get(doc_id)
    if session:
        session["summary_cache"] = summary_json


def get_cached_summary(doc_id: str) -> Optional[str]:
    session = _sessions.get(doc_id)
    if session is None:
        return None
    return session.get("summary_cache")
