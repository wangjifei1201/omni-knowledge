import json
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


class Citation(BaseModel):
    doc_id: str = ""
    doc_name: str = ""
    chapter: str = ""
    section: str = ""
    page: int = 0
    original_text: str = ""
    confidence: float = 0.0
    chunk_id: str = ""


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    question: str = Field(..., min_length=1)
    search_mode: str = "hybrid"  # hybrid / semantic / keyword
    doc_scope: list[str] = []  # specific doc IDs to search within
    detail_level: str = "normal"  # brief / normal / detailed


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    citations: list[Citation] = []
    confidence: float = 0.0
    intent_type: str = "content"
    response_time_ms: int = 0
    related_questions: list[str] = []


class ConversationResponse(BaseModel):
    id: str
    title: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: list[Citation] | None = None
    confidence: float
    feedback: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("citations", mode="before")
    @classmethod
    def parse_citations(cls, v: Any) -> list[Citation] | None:
        """Convert JSON string to list for MySQL compatibility"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                data = json.loads(v)
                return [Citation(**item) if isinstance(item, dict) else item for item in data]
            except (json.JSONDecodeError, TypeError):
                return None
        if isinstance(v, list):
            return [Citation(**item) if isinstance(item, dict) else item for item in v]
        return None


class FeedbackRequest(BaseModel):
    feedback: str = Field(..., pattern="^(like|dislike)$")


class ConversationRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
