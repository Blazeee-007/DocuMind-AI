"""
Utility helpers: text chunking, token estimation, text cleaning,
and cosine similarity for chunk retrieval.
"""
import re
from typing import List, Tuple
import numpy as np


# ---------------------------------------------------------------------------
# Token estimation (rough: 1 token ≈ 4 chars for English text)
# ---------------------------------------------------------------------------

def count_tokens(text: str) -> int:
    """Approximate token count."""
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Strip excessive whitespace and non-printable characters."""
    # Remove null bytes and control characters except newlines/tabs
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Collapse 3+ newlines → 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple spaces
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Text chunking (sliding window)
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_tokens: int = 2000,
    overlap_tokens: int = 200,
) -> List[str]:
    """
    Split text into chunks of ~chunk_tokens with overlap_tokens overlap.
    Uses character-based approximation (1 token ≈ 4 chars).
    """
    chunk_chars = chunk_tokens * 4
    overlap_chars = overlap_tokens * 4

    if len(text) <= chunk_chars:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_chars
        # Try to break on a sentence boundary
        if end < len(text):
            # Look for the last period/newline before the cut
            boundary = text.rfind("\n", start, end)
            if boundary == -1 or boundary < start + chunk_chars // 2:
                boundary = text.rfind(". ", start, end)
            if boundary != -1 and boundary > start:
                end = boundary + 1

        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap_chars

    return [c for c in chunks if c]


# ---------------------------------------------------------------------------
# Reading time
# ---------------------------------------------------------------------------

def reading_time_minutes(word_count: int, wpm: int = 200) -> int:
    """Estimate reading time in minutes (200 wpm default)."""
    return max(1, round(word_count / wpm))


# ---------------------------------------------------------------------------
# Cosine similarity (for chunk retrieval without a vector DB)
# ---------------------------------------------------------------------------

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D numpy arrays."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def top_k_chunks(
    query_embedding: np.ndarray,
    chunk_embeddings: List[np.ndarray],
    chunks: List[str],
    k: int = 4,
) -> List[Tuple[str, float]]:
    """Return top-k chunks by cosine similarity to the query embedding."""
    scores = [cosine_similarity(query_embedding, emb) for emb in chunk_embeddings]
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return ranked[:k]
