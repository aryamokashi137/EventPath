from uuid import UUID
from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin_role

from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectWithActivitiesResponse
)

from app.schemas.simulation import SimulationRequest, SimulationResponse
from app.schemas.crashing import ProjectCrashRequest, ProjectCrashResponse
from app.schemas.monte_carlo import MonteCarloRequest, MonteCarloResponse
from app.schemas.availability import AvailabilityCheckResponse

from app.services import project_service, export_service


router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_role)]
)
def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db)
):
    """Create a new CPM or PERT project (Admin Only)."""
    return project_service.create_project(db, project_in)


@router.get(
    "",
    response_model=List[ProjectResponse]
)
def get_projects(
    db: Session = Depends(get_db)
):
    """Fetch all projects."""
    return project_service.get_projects(db)


@router.get(
    "/{project_id}",
    response_model=ProjectWithActivitiesResponse
)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """Fetch a project with all its activities and dependencies."""
    return project_service.get_project_or_404(db, project_id)


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    dependencies=[Depends(require_admin_role)]
)
def update_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """Update general project details (Admin Only)."""
    return project_service.update_project(
        db,
        project_id,
        project_in
    )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_role)]
)
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a project and all its activities (Admin Only)."""
    project_service.delete_project(db, project_id)
    return None


@router.get("/{project_id}/network")
def get_project_network(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Computes the CPM/PERT network.
    """
    return project_service.get_project_network(db, project_id)


@router.get("/{project_id}/pert")
def get_project_pert(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Computes PERT expected duration, variance, and standard deviation.
    """
    return project_service.get_project_pert(db, project_id)


@router.post("/{project_id}/simulate", response_model=SimulationResponse)
def simulate_project(
    project_id: UUID,
    sim_in: SimulationRequest,
    db: Session = Depends(get_db)
):
    """
    Simulates a "What-If" scenario for a single activity's duration.
    """
    return project_service.simulate_project(db, project_id, sim_in)


@router.post(
    "/{project_id}/crash",
    response_model=ProjectCrashResponse,
    dependencies=[Depends(require_admin_role)]
)
def crash_project(
    project_id: UUID,
    crash_in: ProjectCrashRequest,
    db: Session = Depends(get_db)
):
    """
    Applies the linear schedule crashing algorithm (Admin Only).
    """
    return project_service.crash_project(db, project_id, crash_in)


@router.post("/{project_id}/monte-carlo", response_model=MonteCarloResponse)
def run_monte_carlo(
    project_id: UUID,
    mc_in: MonteCarloRequest,
    db: Session = Depends(get_db)
):
    """
    Runs a Monte Carlo risk simulation for a PERT project.
    """
    return project_service.run_monte_carlo(db, project_id, mc_in)


@router.post(
    "/template/{template_name}",
    response_model=ProjectWithActivitiesResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_role)]
)
def create_project_from_template(
    template_name: str,
    db: Session = Depends(get_db)
):
    """
    Creates a new project pre-populated from an industry template (Admin Only).
    """
    return project_service.create_project_from_template(
        db,
        template_name
    )


@router.get(
    "/{project_id}/availability",
    response_model=AvailabilityCheckResponse
)
def check_vendor_availability(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Verifies hybrid resource/vendor availability
    and detects overbooking conflicts.
    """
    return project_service.check_vendor_availability(
        db,
        project_id
    )


@router.get("/{project_id}/export/csv")
def export_project_csv(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Exports complete project schedule, CPM floats, PERT calculations,
    crashing options, and vendor assignments to a CSV file.
    """
    csv_content = export_service.generate_project_csv(db, project_id)
    filename = f"eventpath_project_{project_id}_export.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/{project_id}/export/pdf")
def export_project_pdf(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Generates and exports a styled publication-grade PDF report
    for the project schedule and risk analysis.
    """
    pdf_bytes = export_service.generate_project_pdf(db, project_id)
    filename = f"eventpath_project_{project_id}_report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )