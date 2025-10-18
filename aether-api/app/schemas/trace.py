from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


class ContextSchema(BaseModel):
    """Schema for a retrieved context chunk."""

    text: str
    source: str
    score: Optional[float] = None
    metadata: Optional[dict[str, Any]] = None


class TraceCreate(BaseModel):
    """Schema for creating a new trace."""

    project_id: UUID
    query: str = Field(..., min_length=1)
    response: str = Field(..., min_length=1)
    contexts: Optional[list[ContextSchema]] = None
    metadata: Optional[dict[str, Any]] = None
    token_count: Optional[int] = None
    latency_ms: Optional[int] = None
    cost_usd: Optional[float] = None
    timestamp: Optional[datetime] = None


class TraceResponse(BaseModel):
    """Schema for trace response."""

    id: UUID
    project_id: UUID
    query: str
    response: str
    contexts: Optional[list[dict[str, Any]]] = None
    metadata: Optional[dict[str, Any]] = None
    token_count: Optional[int] = None
    latency_ms: Optional[int] = None
    cost_usd: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TraceIngestResponse(BaseModel):
    """Response after ingesting a trace."""

    trace_id: UUID
    status: str = "queued"
