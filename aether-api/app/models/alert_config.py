import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AlertConfig(Base):
    """Alert configuration per project - defines thresholds and Slack webhooks."""

    __tablename__ = "alert_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, unique=True)

    # Slack Integration
    slack_webhook_url = Column(String, nullable=True)
    slack_enabled = Column(Boolean, default=False, nullable=False)

    # Hallucination Detection Thresholds
    hallucination_threshold = Column(Float, default=0.5, nullable=False)  # Alert if faithfulness < this
    hallucination_alerts_enabled = Column(Boolean, default=True, nullable=False)

    # Cost Spike Thresholds
    daily_cost_budget_usd = Column(Float, nullable=True)  # Alert if daily cost exceeds this
    cost_spike_alerts_enabled = Column(Boolean, default=False, nullable=False)

    # Latency Thresholds
    latency_p95_threshold_ms = Column(Integer, nullable=True)  # Alert if p95 latency exceeds this
    latency_alerts_enabled = Column(Boolean, default=False, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="alert_config")
