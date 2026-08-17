from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.activity import ActivityCreate, ActivityUpdate, ActivityResponse
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["activities"])

@router.post("/{project_id}/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def add_activity(project_id: UUID, activity_in: ActivityCreate, db: Session = Depends(get_db)):
    """Add a new activity to a project, specifying its details and predecessors."""
    return project_service.create_activity(db, project_id, activity_in)

@router.put("/{project_id}/activities/{activity_id}", response_model=ActivityResponse)
def update_activity(
    project_id: UUID, 
    activity_id: UUID, 
    activity_in: ActivityUpdate, 
    db: Session = Depends(get_db)
):
    """Update details or dependencies of an existing activity."""
    return project_service.update_activity(db, project_id, activity_id, activity_in)

@router.delete("/{project_id}/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(project_id: UUID, activity_id: UUID, db: Session = Depends(get_db)):
    """Delete an activity and cascade-clean its dependencies."""
    project_service.delete_activity(db, project_id, activity_id)
    return None
