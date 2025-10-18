import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class RAGTrace(Base):
    """RAG Trace model - represents a single query/response interaction."""

    __tablename__ = "rag_traces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    contexts = Column(JSONB)  # Retrieved chunks
    trace_metadata = Column(JSONB)  # Model, params, user_id, etc.
    token_count = Column(Integer)
    latency_ms = Column(Integer)
    cost_usd = Column(Numeric(10, 6))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    project = relationship("Project", back_populates="traces")
    evaluation = relationship(
        "Evaluation", back_populates="trace", uselist=False, cascade="all, delete-orphan"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_project_created", "project_id", "created_at"),
        Index("idx_created_at", "created_at"),
    )
