from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin_role
from app.schemas.activity import ActivityCreate, ActivityUpdate, ActivityResponse
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["activities"])

@router.post(
    "/{project_id}/activities",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_role)]
)
def add_activity(project_id: UUID, activity_in: ActivityCreate, db: Session = Depends(get_db)):
    """Add a new activity to a project (Admin Only)."""
    return project_service.create_activity(db, project_id, activity_in)

@router.put(
    "/{project_id}/activities/{activity_id}",
    response_model=ActivityResponse,
    dependencies=[Depends(require_admin_role)]
)
def update_activity(
    project_id: UUID, 
    activity_id: UUID, 
    activity_in: ActivityUpdate, 
    db: Session = Depends(get_db)
):
    """Update details or dependencies of an existing activity (Admin Only)."""
    return project_service.update_activity(db, project_id, activity_id, activity_in)

@router.delete(
    "/{project_id}/activities/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_role)]
)
def delete_activity(project_id: UUID, activity_id: UUID, db: Session = Depends(get_db)):
    """Delete an activity and cascade-clean its dependencies (Admin Only)."""
    project_service.delete_activity(db, project_id, activity_id)
    return None
