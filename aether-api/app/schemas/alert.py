"""
Pydantic schemas for Alerts
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

from app.models.alert import AlertType, Severity


class AlertResponse(BaseModel):
    """Schema for alert response."""
    id: UUID
    project_id: UUID
    alert_type: AlertType
    severity: Severity
    message: str
    alert_metadata: Optional[Dict[str, Any]] = None
    resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Schema for alert list response."""
    alerts: list[AlertResponse]
    total: int
    unresolved_count: int
