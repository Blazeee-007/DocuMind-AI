from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    word_count: int
    page_count: int
    reading_time_minutes: int
    char_count: int
    message: str = "File uploaded and parsed successfully"


class AnalyzeResponse(BaseModel):
    doc_id: str
    executive_summary: str
    key_points: List[str]
    main_topics: List[str]
    tone: str
    word_count: int
    model_used: str


class ExtractResponse(BaseModel):
    doc_id: str
    entities: List[Dict[str, str]]
    key_facts: List[str]
    tables: List[Dict[str, Any]]
    lists: List[str]
    model_used: str


class ChatRequest(BaseModel):
    question: str


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str


class ChatResponse(BaseModel):
    doc_id: str
    question: str
    answer: str
    sources: List[str]
    model_used: str


class HistoryResponse(BaseModel):
    doc_id: str
    messages: List[ChatMessage]
    total_messages: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int
