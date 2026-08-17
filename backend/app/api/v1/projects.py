from uuid import UUID
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectWithActivitiesResponse
)
from app.schemas.simulation import SimulationRequest, SimulationResponse
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new CPM or PERT project."""
    return project_service.create_project(db, project_in)

@router.get("/{project_id}", response_model=ProjectWithActivitiesResponse)
def get_project(project_id: UUID, db: Session = Depends(get_db)):
    """Fetch a project with all its activities and dependencies."""
    return project_service.get_project_or_404(db, project_id)

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: UUID, project_in: ProjectUpdate, db: Session = Depends(get_db)):
    """Update general project details."""
    return project_service.update_project(db, project_id, project_in)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: UUID, db: Session = Depends(get_db)):
    """Delete a project and all its activities."""
    project_service.delete_project(db, project_id)
    return None

@router.get("/{project_id}/network")
def get_project_network(project_id: UUID, db: Session = Depends(get_db)):
    """
    Computes the CPM/PERT network.
    Returns:
    - nodes: all nodes (including virtual START and END) with computed ES, EF, LS, LF, slack, and critical status.
    - edges: dependency arrows.
    - critical_path: ordered sequence of critical activity IDs.
    """
    return project_service.compute_network(db, project_id)

@router.get("/{project_id}/pert")
def get_project_pert_analysis(project_id: UUID, db: Session = Depends(get_db)):
    """
    Returns PERT expected duration, project variance, and (if target_completion_date is set)
    the probability of completing the project on time.
    """
    return project_service.compute_pert_analysis(db, project_id)

@router.post("/{project_id}/simulate", response_model=SimulationResponse)
def simulate_project_change(
    project_id: UUID, 
    request: SimulationRequest, 
    db: Session = Depends(get_db)
):
    """
    Accepts a hypothetical change (updates to one activity's duration/estimates or dependencies)
    and returns the recomputed network delta without committing to the database.
    """
    return project_service.simulate_change(db, project_id, request)
