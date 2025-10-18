from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models import Project
from pydantic import BaseModel


router = APIRouter()


class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: str
    description: Optional[str] = None
    environment: str = "development"


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: UUID
    name: str
    description: Optional[str]
    environment: str
    org_id: UUID

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(db: Session = Depends(get_db)):
    """List all projects (will add auth filtering later)."""
    projects = db.query(Project).all()
    return projects


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project (will add org_id from auth later)."""
    # TODO: Get org_id from authenticated user
    # For now, this is a placeholder
    raise HTTPException(status_code=501, detail="Auth integration pending")
