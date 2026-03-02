import uuid
from datetime import datetime, timezone

from core.config import get_settings
from core.database import Base
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from sqlalchemy.dialects.postgresql import JSON as PGJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Use appropriate JSON type based on database
settings = get_settings()
JSONType = JSON  # SQLAlchemy will handle dialect automatically


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_name: Mapped[str] = mapped_column(String(500), index=True)
    file_path: Mapped[str] = mapped_column(String(1000))  # MinIO path
    file_type: Mapped[str] = mapped_column(String(20))  # pdf, docx, xlsx, etc.
    file_size: Mapped[int] = mapped_column(Integer, default=0)  # bytes
    department: Mapped[str] = mapped_column(String(100), index=True, default="")
    category: Mapped[str] = mapped_column(String(100), index=True, default="")
    security_level: Mapped[str] = mapped_column(String(20), default="内部")
    version: Mapped[str] = mapped_column(String(20), default="v1.0")
    description: Mapped[str] = mapped_column(Text, default="")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    # Processing status
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / processing / completed / failed
    parse_progress: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str] = mapped_column(Text, default="")

    # Chunking strategy configuration
    chunking_strategy: Mapped[str] = mapped_column(String(20), default="paragraph")
    chunking_params: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    # Metadata - use Text for MySQL 5.7 compatibility, store as JSON string
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: ["tag1", "tag2"]
    metadata_extra: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    effective_date: Mapped[str] = mapped_column(String(20), default="")

    # Relations
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    chapters = relationship("Chapter", back_populates="document", lazy="selectin")


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)
    chapter_title: Mapped[str] = mapped_column(String(500), default="")
    level: Mapped[int] = mapped_column(Integer, default=1)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    page_start: Mapped[int] = mapped_column(Integer, default=0)
    page_end: Mapped[int] = mapped_column(Integer, default=0)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    document = relationship("Document", back_populates="chapters")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)
    chapter_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    chunk_type: Mapped[str] = mapped_column(String(20), default="text")  # text / table / image
    content: Mapped[str] = mapped_column(Text)
    content_markdown: Mapped[str] = mapped_column(Text, default="")
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: {x, y, w, h}
    metadata_extra: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    milvus_id: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), index=True)
    tag_name: Mapped[str] = mapped_column(String(100), index=True)
