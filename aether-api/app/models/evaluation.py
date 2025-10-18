import uuid
from datetime import datetime
from sqlalchemy import Column, Boolean, DateTime, ForeignKey, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Evaluation(Base):
    """Evaluation model - stores computed metrics for a trace."""

    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(UUID(as_uuid=True), ForeignKey("rag_traces.id"), nullable=False, unique=True)

    # Retrieval metrics
    context_precision = Column(Numeric(3, 2))
    context_recall = Column(Numeric(3, 2))

    # Generation metrics
    answer_relevancy = Column(Numeric(3, 2))
    faithfulness = Column(Numeric(3, 2))

    # Safety metrics
    hallucination_detected = Column(Boolean)
    toxicity_score = Column(Numeric(3, 2))
    pii_detected = Column(Boolean)

    # Fast metrics (computed without LLM)
    token_overlap_ratio = Column(Numeric(3, 2))
    answer_length = Column(Numeric(10, 2))

    # Metadata
    evaluation_cost_usd = Column(Numeric(10, 6))  # Cost of running evaluation
    evaluated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    trace = relationship("RAGTrace", back_populates="evaluation")

    __table_args__ = (Index("idx_trace", "trace_id"),)
