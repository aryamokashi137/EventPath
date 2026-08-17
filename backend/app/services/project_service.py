from uuid import UUID
from datetime import date
from typing import List, Dict, Tuple, Optional, Set
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.project import Project
from app.models.activity import Activity
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.activity import ActivityCreate, ActivityUpdate
from app.schemas.simulation import SimulationRequest, SimulationResponse
from app.services import cpm_engine

def get_project_or_404(db: Session, project_id: UUID) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_RESOURCE_NOT_FOUND if hasattr(status, "HTTP_404_RESOURCE_NOT_FOUND") else 404,
            detail=f"Project with ID {project_id} not found."
        )
    return project

def get_activity_or_404(db: Session, activity_id: UUID) -> Activity:
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(
            status_code=404,
            detail=f"Activity with ID {activity_id} not found."
        )
    return activity

def create_project(db: Session, project_in: ProjectCreate) -> Project:
    project = Project(
        name=project_in.name,
        description=project_in.description,
        target_completion_date=project_in.target_completion_date,
        mode=project_in.mode.value
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

def update_project(db: Session, project_id: UUID, project_in: ProjectUpdate) -> Project:
    project = get_project_or_404(db, project_id)
    update_data = project_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "mode":
            setattr(project, field, value.value)
        else:
            setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project

def delete_project(db: Session, project_id: UUID) -> None:
    project = get_project_or_404(db, project_id)
    db.delete(project)
    db.commit()

def create_activity(db: Session, project_id: UUID, activity_in: ActivityCreate) -> Activity:
    # Ensure project exists
    project = get_project_or_404(db, project_id)
    
    # Verify project mode requirements
    if project.mode == "CPM" and activity_in.duration <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if hasattr(status, "HTTP_400_BAD_REQUEST") else 400,
            detail="Duration must be greater than zero for CPM projects."
        )
    if project.mode == "PERT" and (
        activity_in.optimistic_time is None or 
        activity_in.most_likely_time is None or 
        activity_in.pessimistic_time is None
    ):
        raise HTTPException(
            status_code=400,
            detail="PERT time estimates (optimistic, most_likely, pessimistic) are required for PERT projects."
        )

    # Check predecessors exist and belong to the same project
    predecessors = []
    for pred_id in activity_in.predecessor_ids:
        pred = db.query(Activity).filter(Activity.id == pred_id).first()
        if not pred:
            raise HTTPException(
                status_code=404,
                detail=f"Predecessor activity with ID {pred_id} not found."
            )
        if pred.project_id != project_id:
            raise HTTPException(
                status_code=400,
                detail=f"Predecessor activity {pred_id} belongs to a different project."
            )
        predecessors.append(pred)

    activity = Activity(
        project_id=project_id,
        name=activity_in.name,
        duration=activity_in.duration,
        optimistic_time=activity_in.optimistic_time,
        most_likely_time=activity_in.most_likely_time,
        pessimistic_time=activity_in.pessimistic_time,
        predecessors=predecessors
    )
    db.add(activity)
    
    # Temp check for circular dependencies before committing
    db.flush()
    try:
        # Build in-memory list to dry run cycle detection
        activities_data = _prepare_cpm_input_from_db(db, project_id)
        # Run cycle detection
        nodes = cpm_engine.build_network(activities_data)
        cpm_engine.detect_cycles_and_sort(nodes)
    except cpm_engine.CycleDetectedError as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error validating dependencies: {str(e)}"
        )

    db.commit()
    db.refresh(activity)
    return activity

def update_activity(db: Session, project_id: UUID, activity_id: UUID, activity_in: ActivityUpdate) -> Activity:
    project = get_project_or_404(db, project_id)
    activity = get_activity_or_404(db, activity_id)
    
    if activity.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Activity does not belong to this project."
        )

    update_data = activity_in.model_dump(exclude_unset=True)
    
    # Save current predecessors to rollback if circular dependency detected
    old_predecessors = list(activity.predecessors)
    
    if "predecessor_ids" in update_data:
        pred_ids = update_data.pop("predecessor_ids")
        predecessors = []
        for pred_id in pred_ids:
            if pred_id == activity_id:
                raise HTTPException(
                    status_code=400,
                    detail="An activity cannot depend on itself."
                )
            pred = db.query(Activity).filter(Activity.id == pred_id).first()
            if not pred:
                raise HTTPException(
                    status_code=404,
                    detail=f"Predecessor activity with ID {pred_id} not found."
                )
            if pred.project_id != project_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Predecessor activity {pred_id} belongs to a different project."
                )
            predecessors.append(pred)
        activity.predecessors = predecessors

    for field, value in update_data.items():
        setattr(activity, field, value)

    # Validate that we still satisfy PERT bounds if updated
    if project.mode == "PERT":
        opt = activity.optimistic_time if activity.optimistic_time is not None else 0.0
        lk = activity.most_likely_time if activity.most_likely_time is not None else 0.0
        pes = activity.pessimistic_time if activity.pessimistic_time is not None else 0.0
        # If some were updated and some weren't, we validate the merged state
        if not (opt <= lk <= pes):
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="PERT estimates must satisfy: optimistic <= most_likely <= pessimistic"
            )

    db.flush()
    # Check for cycles
    try:
        activities_data = _prepare_cpm_input_from_db(db, project_id)
        nodes = cpm_engine.build_network(activities_data)
        cpm_engine.detect_cycles_and_sort(nodes)
    except cpm_engine.CycleDetectedError as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error validating changes: {str(e)}"
        )

    db.commit()
    db.refresh(activity)
    return activity

def delete_activity(db: Session, project_id: UUID, activity_id: UUID) -> None:
    project = get_project_or_404(db, project_id)
    activity = get_activity_or_404(db, activity_id)
    
    if activity.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Activity does not belong to this project."
        )

    db.delete(activity)
    db.commit()

def compute_network(db: Session, project_id: UUID) -> Dict:
    project = get_project_or_404(db, project_id)
    activities_data = _prepare_cpm_input_from_db(db, project_id)
    
    if project.mode == "CPM":
        nodes, critical_path, duration = cpm_engine.calculate_cpm(activities_data)
    else:  # PERT
        nodes, critical_path, duration, _, _ = cpm_engine.calculate_pert(activities_data)

    # Format nodes
    formatted_nodes = []
    for node_id, node in nodes.items():
        formatted_nodes.append({
            "id": node.id,
            "name": node.name,
            "duration": node.duration,
            "es": node.es,
            "ef": node.ef,
            "ls": node.ls,
            "lf": node.lf,
            "slack": node.slack,
            "is_critical": node.is_critical
        })

    # Format edges
    edges = []
    for node_id, node in nodes.items():
        for succ_id in node.successors:
            edges.append({
                "from_node": node_id,
                "to_node": succ_id
            })

    # Convert critical path IDs to UUIDs (excluding virtual START and END)
    critical_path_uuids = [UUID(cid) for cid in critical_path]

    return {
        "nodes": formatted_nodes,
        "edges": edges,
        "critical_path": critical_path_uuids
    }

def compute_pert_analysis(db: Session, project_id: UUID) -> Dict:
    project = get_project_or_404(db, project_id)
    if project.mode != "PERT":
        raise HTTPException(
            status_code=400,
            detail="PERT calculations are only available for projects in PERT mode."
        )

    activities_data = _prepare_cpm_input_from_db(db, project_id)
    
    target_time = None
    if project.target_completion_date is not None:
        # Calculate target time as difference in days between target completion and project created_at
        # Use datetime.date() to ensure comparison is between date objects
        start_date = project.created_at.date()
        target_time = float((project.target_completion_date - start_date).days)

    nodes, critical_path, expected_duration, variance, probability = cpm_engine.calculate_pert(
        activities_data, target_time=target_time
    )

    return {
        "expected_project_duration": expected_duration,
        "project_variance": variance,
        "probability": probability
    }

def simulate_change(db: Session, project_id: UUID, request: SimulationRequest) -> Dict:
    project = get_project_or_404(db, project_id)
    activities_data = _prepare_cpm_input_from_db(db, project_id)
    
    # 1. Run baseline calculation to find currently critical activities
    if project.mode == "CPM":
        baseline_nodes, baseline_critical, _ = cpm_engine.calculate_cpm(activities_data)
    else:
        baseline_nodes, baseline_critical, _, _, _ = cpm_engine.calculate_pert(activities_data)
        
    baseline_critical_set = set(baseline_critical)

    # 2. Apply simulated changes to activities_data in-memory
    simulated_activity_id = str(request.activity_id)
    activity_found = False
    
    for act in activities_data:
        if act["id"] == simulated_activity_id:
            activity_found = True
            if request.name is not None:
                act["name"] = request.name
            if request.duration is not None:
                act["duration"] = request.duration
            if request.optimistic_time is not None:
                act["optimistic_time"] = request.optimistic_time
            if request.most_likely_time is not None:
                act["most_likely_time"] = request.most_likely_time
            if request.pessimistic_time is not None:
                act["pessimistic_time"] = request.pessimistic_time
            if request.predecessor_ids is not None:
                # Convert list of UUIDs to list of strings
                act["predecessor_ids"] = [str(pid) for pid in request.predecessor_ids]
            break

    if not activity_found:
        raise HTTPException(
            status_code=404,
            detail=f"Activity with ID {request.activity_id} not found in this project."
        )

    # 3. Check for cycles in the simulated network
    try:
        sim_nodes = cpm_engine.build_network(activities_data)
        cpm_engine.detect_cycles_and_sort(sim_nodes)
    except cpm_engine.CycleDetectedError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Simulated change creates a loop! {str(e)}"
        )

    # 4. Run simulated calculations
    target_time = None
    if project.target_completion_date is not None:
        start_date = project.created_at.date()
        target_time = float((project.target_completion_date - start_date).days)

    if project.mode == "CPM":
        nodes, new_critical, duration = cpm_engine.calculate_cpm(activities_data)
        probability = None
    else:
        nodes, new_critical, duration, _, probability = cpm_engine.calculate_pert(
            activities_data, target_time=target_time
        )

    new_critical_set = set(new_critical)

    # Calculate flipped lists
    flipped_to_critical = list(new_critical_set - baseline_critical_set)
    flipped_to_non_critical = list(baseline_critical_set - new_critical_set)

    return {
        "new_critical_path": [UUID(cid) for cid in new_critical],
        "new_project_duration": duration,
        "new_completion_probability": probability,
        "flipped_to_critical": [UUID(cid) for cid in flipped_to_critical],
        "flipped_to_non_critical": [UUID(cid) for cid in flipped_to_non_critical]
    }


def _prepare_cpm_input_from_db(db: Session, project_id: UUID) -> List[Dict]:
    activities = db.query(Activity).filter(Activity.project_id == project_id).all()
    activities_data = []
    for act in activities:
        activities_data.append({
            "id": str(act.id),
            "name": act.name,
            "duration": act.duration,
            "optimistic_time": act.optimistic_time,
            "most_likely_time": act.most_likely_time,
            "pessimistic_time": act.pessimistic_time,
            "predecessor_ids": [str(pred.id) for pred in act.predecessors]
        })
    return activities_data
