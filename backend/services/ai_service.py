"""
AI Service — wraps an LLM API for summarization, extraction, and Q&A.
Uses map-reduce for large documents and sentence-transformers for chunk retrieval.
"""
import json
import os
import re
from typing import Dict, Any, List, Optional

import anthropic
import numpy as np
from dotenv import load_dotenv

from backend.utils.helpers import chunk_text, top_k_chunks

load_dotenv()

API_KEY = os.getenv("API_KEY", os.getenv("ANTHROPIC_API_KEY", ""))
MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 4096

_client: Optional[anthropic.Anthropic] = None
_embedder = None  # sentence-transformers model, lazy loaded


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=API_KEY)
    return _client


def get_embedder():
    """Lazy-load sentence-transformers model (downloads on first call)."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


# ---------------------------------------------------------------------------
# Helper — call the LLM with a plain prompt
# ---------------------------------------------------------------------------

def _call_llm(prompt: str, max_tokens: int = MAX_TOKENS) -> str:
    client = get_client()
    message = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


# ---------------------------------------------------------------------------
# Summarization — map-reduce for multi-chunk documents
# ---------------------------------------------------------------------------

SUMMARIZE_CHUNK_PROMPT = """You are a document analyst. Summarize the following section concisely, 
capturing the main ideas, key entities, and important facts.

Section:
{text}

Provide a clear, dense summary in 3-5 sentences."""

SUMMARIZE_FINAL_PROMPT = """You are a document analyst. Given the following partial summaries of a document, 
produce a comprehensive final analysis.

Partial summaries:
{summaries}

Provide a structured response in EXACTLY this JSON format (no markdown fences, raw JSON only):
{{
  "executive_summary": "A 3-sentence executive summary of the entire document",
  "key_points": ["point 1", "point 2", "point 3", "point 4", "point 5"],
  "main_topics": ["topic 1", "topic 2", "topic 3"],
  "tone": "formal | technical | casual | academic | conversational | persuasive"
}}"""


def summarize_document(text: str) -> Dict[str, Any]:
    """Map-reduce summarization using the LLM."""
    chunks = chunk_text(text, chunk_tokens=3000, overlap_tokens=100)

    if len(chunks) == 1:
        # Short document — single pass
        partial_summaries = [text[:12000]]
    else:
        # Map step — summarize each chunk
        partial_summaries = []
        for chunk in chunks:
            summary = _call_llm(
                SUMMARIZE_CHUNK_PROMPT.format(text=chunk), max_tokens=512
            )
            partial_summaries.append(summary)

    # Reduce step — synthesize all partial summaries
    combined = "\n\n---\n\n".join(partial_summaries)
    # Truncate combined if too large
    if len(combined) > 20000:
        combined = combined[:20000] + "...[truncated]"

    final_prompt = SUMMARIZE_FINAL_PROMPT.format(summaries=combined)
    raw = _call_llm(final_prompt, max_tokens=1024)

    # Parse JSON response
    try:
        # Strip any accidental markdown fences
        raw_clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        data = json.loads(raw_clean)
    except json.JSONDecodeError:
        # Fallback: return raw text wrapped in a safe structure
        data = {
            "executive_summary": raw[:500],
            "key_points": ["See full summary above"],
            "main_topics": ["General"],
            "tone": "unknown",
        }

    data["model_used"] = MODEL
    return data


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

EXTRACT_PROMPT = """You are a document data extraction specialist.
Analyze the following document and extract structured information.

Document:
{text}

Respond in EXACTLY this JSON format (raw JSON, no markdown fences):
{{
  "entities": [
    {{"type": "PERSON|ORG|DATE|LOCATION|MONEY|OTHER", "value": "entity text"}}
  ],
  "key_facts": ["fact 1", "fact 2", "fact 3", "fact 4", "fact 5"],
  "tables": [
    {{
      "title": "table title or description",
      "headers": ["col1", "col2"],
      "rows": [["val1", "val2"]]
    }}
  ],
  "lists": ["list item 1", "list item 2"]
}}

Extract up to 15 entities, 8 key facts, all tables, and up to 20 list items."""


def extract_data(text: str) -> Dict[str, Any]:
    """Extract structured entities, facts, and tables from document text."""
    # Use only first ~8000 chars for extraction to keep cost low
    excerpt = text[:8000] if len(text) > 8000 else text
    prompt = EXTRACT_PROMPT.format(text=excerpt)
    raw = _call_llm(prompt, max_tokens=2048)

    try:
        raw_clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        data = json.loads(raw_clean)
    except json.JSONDecodeError:
        data = {
            "entities": [],
            "key_facts": [raw[:300]],
            "tables": [],
            "lists": [],
        }

    data["model_used"] = MODEL
    return data


# ---------------------------------------------------------------------------
# Q&A — RAG with sentence-transformers + LLM
# ---------------------------------------------------------------------------

QA_PROMPT = """You are an assistant helping a user understand a document.
Answer ONLY based on the document context provided below.
If the answer is not in the document, say so clearly.
Be concise, helpful, and cite the relevant section when possible.

Document context:
{context}

User question: {question}

Answer:"""


def embed_chunks(chunks: List[str]) -> List[np.ndarray]:
    """Compute embeddings for all chunks using sentence-transformers."""
    embedder = get_embedder()
    embeddings = embedder.encode(chunks, convert_to_numpy=True, show_progress_bar=False)
    return [embeddings[i] for i in range(len(chunks))]


def answer_question(
    question: str,
    chunks: List[str],
    embeddings: Optional[List[np.ndarray]],
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """RAG-style Q&A: retrieve top-k chunks then ask the LLM."""
    if embeddings is None:
        embeddings = embed_chunks(chunks)

    # Embed the question
    embedder = get_embedder()
    q_embedding = embedder.encode([question], convert_to_numpy=True, show_progress_bar=False)[0]

    # Retrieve top-4 relevant chunks
    top_chunks = top_k_chunks(q_embedding, embeddings, chunks, k=4)
    context = "\n\n---\n\n".join(chunk for chunk, _ in top_chunks)

    # Truncate context if needed
    if len(context) > 12000:
        context = context[:12000] + "...[truncated]"

    prompt = QA_PROMPT.format(context=context, question=question)
    answer = _call_llm(prompt, max_tokens=1024)

    sources = [chunk[:120].replace("\n", " ") + "..." for chunk, _ in top_chunks if chunk.strip()]

    return {
        "answer": answer,
        "sources": sources,
        "embeddings": embeddings,  # Return so caller can cache
        "model_used": MODEL,
    }
