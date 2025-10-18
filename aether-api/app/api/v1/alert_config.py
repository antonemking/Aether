"""
Alert Configuration API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.models import AlertConfig, Project
from app.schemas.alert_config import AlertConfigCreate, AlertConfigUpdate, AlertConfigResponse

router = APIRouter()


@router.get("/{project_id}", response_model=AlertConfigResponse)
async def get_alert_config(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get alert configuration for a project.
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get or create alert config
    alert_config = db.query(AlertConfig).filter(AlertConfig.project_id == project_id).first()

    if not alert_config:
        # Create default alert config
        alert_config = AlertConfig(project_id=project_id)
        db.add(alert_config)
        db.commit()
        db.refresh(alert_config)

    return alert_config


@router.post("/{project_id}", response_model=AlertConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_config(
    project_id: UUID,
    config: AlertConfigCreate,
    db: Session = Depends(get_db)
):
    """
    Create alert configuration for a project.
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check if config already exists
    existing_config = db.query(AlertConfig).filter(AlertConfig.project_id == project_id).first()
    if existing_config:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Alert configuration already exists for this project"
        )

    # Create new config
    alert_config = AlertConfig(
        project_id=project_id,
        **config.model_dump()
    )
    db.add(alert_config)
    db.commit()
    db.refresh(alert_config)

    return alert_config


@router.put("/{project_id}", response_model=AlertConfigResponse)
async def update_alert_config(
    project_id: UUID,
    config: AlertConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    Update alert configuration for a project.
    """
    # Get existing config
    alert_config = db.query(AlertConfig).filter(AlertConfig.project_id == project_id).first()

    if not alert_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert configuration not found. Create one first."
        )

    # Update only provided fields
    update_data = config.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(alert_config, key, value)

    db.commit()
    db.refresh(alert_config)

    return alert_config


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_config(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete alert configuration for a project (resets to defaults).
    """
    alert_config = db.query(AlertConfig).filter(AlertConfig.project_id == project_id).first()

    if not alert_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert configuration not found"
        )

    db.delete(alert_config)
    db.commit()

    return None
