"""
Alert Management API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.models import Alert, Project, AlertType, Severity
from app.schemas.alert import AlertResponse, AlertListResponse

router = APIRouter()


@router.get("/{project_id}", response_model=AlertListResponse)
async def get_alerts(
    project_id: UUID,
    alert_type: Optional[AlertType] = None,
    severity: Optional[Severity] = None,
    resolved: Optional[bool] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get alerts for a project with optional filtering.

    Query parameters:
    - alert_type: Filter by alert type (hallucination, cost_spike, high_latency, etc.)
    - severity: Filter by severity (info, warning, critical)
    - resolved: Filter by resolution status
    - limit: Number of alerts to return (default 50, max 200)
    - offset: Number of alerts to skip (for pagination)
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Build query
    query = db.query(Alert).filter(Alert.project_id == project_id)

    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)

    if severity:
        query = query.filter(Alert.severity == severity)

    if resolved is not None:
        query = query.filter(Alert.resolved == resolved)

    # Get total count
    total = query.count()

    # Get unresolved count
    unresolved_count = db.query(func.count(Alert.id)).filter(
        Alert.project_id == project_id,
        Alert.resolved == False
    ).scalar()

    # Get alerts ordered by created_at desc
    alerts = query.order_by(desc(Alert.created_at)).limit(limit).offset(offset).all()

    return {
        "alerts": alerts,
        "total": total,
        "unresolved_count": unresolved_count or 0
    }


@router.get("/{project_id}/{alert_id}", response_model=AlertResponse)
async def get_alert(
    project_id: UUID,
    alert_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific alert by ID.
    """
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.project_id == project_id
    ).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    return alert


@router.put("/{project_id}/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    project_id: UUID,
    alert_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Mark an alert as resolved.
    """
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.project_id == project_id
    ).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    alert.resolved = True
    db.commit()
    db.refresh(alert)

    return alert


@router.put("/{project_id}/{alert_id}/unresolve", response_model=AlertResponse)
async def unresolve_alert(
    project_id: UUID,
    alert_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Mark an alert as unresolved.
    """
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.project_id == project_id
    ).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    alert.resolved = False
    db.commit()
    db.refresh(alert)

    return alert


@router.delete("/{project_id}/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    project_id: UUID,
    alert_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete an alert.
    """
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.project_id == project_id
    ).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    db.delete(alert)
    db.commit()

    return None
