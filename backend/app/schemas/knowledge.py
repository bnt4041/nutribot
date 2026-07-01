"""Pydantic schemas for knowledge-base documents."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentStatus


class DocumentCreate(BaseModel):
    """Payload to add (and index) a knowledge document."""

    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., min_length=1)
    source: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=1024)


class DocumentOut(BaseModel):
    """Document metadata returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source: str | None
    source_url: str | None
    status: DocumentStatus
    chunk_count: int
    indexed_at: datetime | None
    created_at: datetime


class RetrievedChunkOut(BaseModel):
    """A single retrieval hit (used by the debug search endpoint)."""

    document_id: int
    document_title: str
    chunk_text: str
    similarity: float
