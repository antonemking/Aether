import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class EnvironmentType(str, enum.Enum):
    """Environment types for projects."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Project(Base):
    """Project model - customers can have multiple RAG systems."""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    environment = Column(
        Enum(EnvironmentType), nullable=False, default=EnvironmentType.DEVELOPMENT
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="projects")
    traces = relationship("RAGTrace", back_populates="project", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="project", cascade="all, delete-orphan")
    alert_config = relationship("AlertConfig", back_populates="project", uselist=False, cascade="all, delete-orphan")
