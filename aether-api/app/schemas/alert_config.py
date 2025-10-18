"""
Pydantic schemas for Alert Configuration
"""
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class AlertConfigBase(BaseModel):
    """Base schema for alert configuration."""
    slack_webhook_url: Optional[str] = None
    slack_enabled: bool = False
    hallucination_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    hallucination_alerts_enabled: bool = True
    daily_cost_budget_usd: Optional[float] = Field(default=None, ge=0.0)
    cost_spike_alerts_enabled: bool = False
    latency_p95_threshold_ms: Optional[int] = Field(default=None, ge=0)
    latency_alerts_enabled: bool = False


class AlertConfigCreate(AlertConfigBase):
    """Schema for creating alert configuration."""
    pass


class AlertConfigUpdate(BaseModel):
    """Schema for updating alert configuration (all fields optional)."""
    slack_webhook_url: Optional[str] = None
    slack_enabled: Optional[bool] = None
    hallucination_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    hallucination_alerts_enabled: Optional[bool] = None
    daily_cost_budget_usd: Optional[float] = Field(default=None, ge=0.0)
    cost_spike_alerts_enabled: Optional[bool] = None
    latency_p95_threshold_ms: Optional[int] = Field(default=None, ge=0)
    latency_alerts_enabled: Optional[bool] = None


class AlertConfigResponse(AlertConfigBase):
    """Schema for alert configuration response."""
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
