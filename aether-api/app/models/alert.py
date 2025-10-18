import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class AlertType(str, enum.Enum):
    """Types of alerts."""

    QUALITY_DROP = "quality_drop"
    COST_SPIKE = "cost_spike"
    HALLUCINATION = "hallucination"
    HIGH_LATENCY = "high_latency"
    ERROR_RATE = "error_rate"


class Severity(str, enum.Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert(Base):
    """Alert model - represents system alerts for projects."""

    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    alert_type = Column(Enum(AlertType), nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    message = Column(String, nullable=False)
    alert_metadata = Column(JSONB)
    resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="alerts")
