import json
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, field_validator, model_validator


class DocumentCreate(BaseModel):
    doc_name: str
    department: str = ""
    category: str = ""
    security_level: str = "内部"
    tags: list[str] = []
    description: str = ""
    effective_date: str = ""


class DocumentUpdate(BaseModel):
    doc_name: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None
    security_level: Optional[str] = None
    tags: Optional[list[str]] = None
    description: Optional[str] = None
    effective_date: Optional[str] = None


class DocumentResponse(BaseModel):
    id: str
    doc_name: str
    file_type: str
    file_size: int
    department: str
    category: str
    security_level: str
    version: str
    description: str
    page_count: int
    chunk_count: int
    status: str
    parse_progress: float
    tags: list[str] | None
    effective_date: str
    chunking_strategy: str = "paragraph"
    chunking_params: dict | None = None
    uploaded_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v: Any) -> list[str] | None:
        """Convert JSON string to list for MySQL compatibility"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        if isinstance(v, list):
            return v
        return []

    @field_validator("chunking_params", mode="before")
    @classmethod
    def parse_chunking_params(cls, v: Any) -> dict | None:
        """Convert JSON string to dict"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        if isinstance(v, dict):
            return v
        return None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentFilter(BaseModel):
    keyword: str = ""
    department: str = ""
    category: str = ""
    file_type: str = ""
    status: str = ""
    security_level: str = ""
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"


class ChapterResponse(BaseModel):
    id: str
    chapter_title: str
    level: int
    parent_id: str | None
    page_start: int
    page_end: int
    order_index: int

    model_config = {"from_attributes": True}


class ChunkResponse(BaseModel):
    id: str
    chunk_index: int
    content: str
    token_count: int
    chunk_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChunkListResponse(BaseModel):
    items: list[ChunkResponse]
    total: int
    page: int
    page_size: int


class ChunkingConfigUpdate(BaseModel):
    chunking_strategy: str  # character / paragraph / heading
    chunking_params: dict = {}
