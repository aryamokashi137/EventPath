import asyncio
from uuid import UUID
from datetime import date
from typing import List, Dict, Tuple, Optional, Set

from sqlalchemy.orm import Session
from sqlalchemy import select, delete, insert
from fastapi import HTTPException, status

from app.models.project import Project
from app.models.activity import Activity, activity_dependencies
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.activity import ActivityCreate, ActivityUpdate, DependencySpec
from app.schemas.simulation import SimulationRequest, SimulationResponse
from app.schemas.crashing import ProjectCrashRequest, ProjectCrashResponse
from app.schemas.monte_carlo import MonteCarloRequest, MonteCarloResponse
from app.services import cpm_engine
from app.core.websocket import ws_manager


def notify_ws_update(project_id: UUID, event_type: str, details: Optional[Dict] = None):
    """Broadcasting helper to push real-time project updates to connected WebSocket clients."""
    try:
        payload = {
            "event": event_type,
            "project_id": str(project_id),
            "details": details or {}
        }
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(ws_manager.broadcast(str(project_id), payload))
    except Exception:
        pass


def get_project_or_404(db: Session, project_id: UUID) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project with ID {project_id} not found."
        )

    return project


def get_projects(db: Session) -> List[Project]:
    """Return all projects."""
    return db.query(Project).order_by(Project.created_at.desc()).all()


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
        start_date=project_in.start_date,
        category=project_in.category,
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
    notify_ws_update(project_id, "PROJECT_UPDATED", {"project_id": str(project_id)})
    return project

def delete_project(db: Session, project_id: UUID) -> None:
    project = get_project_or_404(db, project_id)
    db.delete(project)
    db.commit()
    notify_ws_update(project_id, "PROJECT_DELETED", {"project_id": str(project_id)})


def _process_dependency_inputs(
    db: Session,
    project_id: UUID,
    activity_id: Optional[UUID],
    dependencies_input: Optional[List[DependencySpec]],
    predecessor_ids_input: Optional[List[UUID]]
) -> Tuple[List[Activity], List[Dict]]:
    """Helper to validate and construct dependency structures."""
    raw_deps = []
    
    if dependencies_input is not None:
        for dep in dependencies_input:
            raw_deps.append({
                "predecessor_id": dep.predecessor_id,
                "dependency_type": dep.dependency_type.upper(),
                "lag": float(dep.lag)
            })
    elif predecessor_ids_input is not None:
        for p_id in predecessor_ids_input:
            raw_deps.append({
                "predecessor_id": p_id,
                "dependency_type": "FS",
                "lag": 0.0
            })

    predecessors = []
    processed_deps = []
    
    for dep in raw_deps:
        pred_id = dep["predecessor_id"]
        if activity_id and pred_id == activity_id:
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
        processed_deps.append(dep)

    return predecessors, processed_deps


def _sync_activity_dependencies_table(db: Session, activity_id: UUID, processed_deps: List[Dict]):
    """Sync explicit dependency_type and lag into the activity_dependencies association table."""
    for dep in processed_deps:
        db.execute(
            activity_dependencies.update()
            .where(
                (activity_dependencies.c.activity_id == activity_id) &
                (activity_dependencies.c.predecessor_activity_id == dep["predecessor_id"])
            )
            .values(
                dependency_type=dep["dependency_type"],
                lag=dep["lag"]
            )
        )



def create_activity(db: Session, project_id: UUID, activity_in: ActivityCreate) -> Activity:
    project = get_project_or_404(db, project_id)
    
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

    predecessors, processed_deps = _process_dependency_inputs(
        db, project_id, None, activity_in.dependencies, activity_in.predecessor_ids
    )

    activity = Activity(
        project_id=project_id,
        name=activity_in.name,
        duration=activity_in.duration,
        optimistic_time=activity_in.optimistic_time,
        most_likely_time=activity_in.most_likely_time,
        pessimistic_time=activity_in.pessimistic_time,
        crash_duration=activity_in.crash_duration,
        normal_cost=activity_in.normal_cost,
        crash_cost=activity_in.crash_cost,
        category=activity_in.category,
        vendor_name=activity_in.vendor_name,
        is_milestone=activity_in.is_milestone,
        vendor_available_from=activity_in.vendor_available_from,
        vendor_available_to=activity_in.vendor_available_to,
        predecessors=predecessors
    )
    db.add(activity)
    db.flush()

    _sync_activity_dependencies_table(db, activity.id, processed_deps)
    
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
            detail=f"Error validating dependencies: {str(e)}"
        )

    db.commit()
    db.refresh(activity)
    notify_ws_update(project_id, "ACTIVITY_CREATED", {"activity_id": str(activity.id)})
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
    
    deps_provided = "dependencies" in update_data or "predecessor_ids" in update_data
    dependencies_input = update_data.pop("dependencies", None)
    predecessor_ids_input = update_data.pop("predecessor_ids", None)
    
    if deps_provided:
        predecessors, processed_deps = _process_dependency_inputs(
            db, project_id, activity_id, dependencies_input, predecessor_ids_input
        )
        activity.predecessors = predecessors
        _sync_activity_dependencies_table(db, activity.id, processed_deps)

    for field, value in update_data.items():
        setattr(activity, field, value)

    if project.mode == "PERT":
        opt = activity.optimistic_time if activity.optimistic_time is not None else 0.0
        lk = activity.most_likely_time if activity.most_likely_time is not None else 0.0
        pes = activity.pessimistic_time if activity.pessimistic_time is not None else 0.0
        if not (opt <= lk <= pes):
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="PERT estimates must satisfy: optimistic <= most_likely <= pessimistic"
            )

    db.flush()
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
    notify_ws_update(project_id, "ACTIVITY_UPDATED", {"activity_id": str(activity.id)})
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
    notify_ws_update(project_id, "ACTIVITY_DELETED", {"activity_id": str(activity_id)})


def compute_network(db: Session, project_id: UUID) -> Dict:
    project = get_project_or_404(db, project_id)
    activities_data = _prepare_cpm_input_from_db(db, project_id)
    
    is_pert = (project.mode == "PERT")
    if project.mode == "CPM":
        nodes, critical_path, duration = cpm_engine.calculate_cpm(activities_data)
    else:  # PERT
        nodes, critical_path, duration, _, _ = cpm_engine.calculate_pert(activities_data)

    # Format nodes:
    # CPM: solid integer whole days
    # PERT: statistical three-point times (rounded to 3 decimals max, e.g. 7.667 or 7.666 days)
    formatted_nodes = []
    for node_id, node in nodes.items():
        if is_pert:
            formatted_nodes.append({
                "id": node.id,
                "name": node.name,
                "duration": round(node.duration, 3) if node.duration is not None else 0.0,
                "es": round(node.es, 3) if node.es is not None else 0.0,
                "ef": round(node.ef, 3) if node.ef is not None else 0.0,
                "ls": round(node.ls, 3) if node.ls is not None else 0.0,
                "lf": round(node.lf, 3) if node.lf is not None else 0.0,
                "slack": round(node.slack, 3) if node.slack is not None else 0.0,
                "total_float": round(node.total_float, 3) if node.total_float is not None else 0.0,
                "free_float": round(node.free_float, 3) if node.free_float is not None else 0.0,
                "interfering_float": round(node.interfering_float, 3) if node.interfering_float is not None else 0.0,
                "is_critical": node.is_critical
            })
        else:
            formatted_nodes.append({
                "id": node.id,
                "name": node.name,
                "duration": round(node.duration) if node.duration is not None else 0,
                "es": round(node.es) if node.es is not None else 0,
                "ef": round(node.ef) if node.ef is not None else 0,
                "ls": round(node.ls) if node.ls is not None else 0,
                "lf": round(node.lf) if node.lf is not None else 0,
                "slack": round(node.slack) if node.slack is not None else 0,
                "total_float": round(node.total_float) if node.total_float is not None else 0,
                "free_float": round(node.free_float) if node.free_float is not None else 0,
                "interfering_float": round(node.interfering_float) if node.interfering_float is not None else 0,
                "is_critical": node.is_critical
            })

    # Format edges with dependency types (FS, SS, FF, SF) and lag
    edges = []
    for node_id, node in nodes.items():
        if node.successor_specs:
            for spec in node.successor_specs:
                edges.append({
                    "from_node": node_id,
                    "to_node": spec["succ_id"],
                    "dependency_type": spec.get("dependency_type", "FS"),
                    "lag": spec.get("lag", 0.0)
                })
        else:
            for succ_id in node.successors:
                edges.append({
                    "from_node": node_id,
                    "to_node": succ_id,
                    "dependency_type": "FS",
                    "lag": 0.0
                })

    # Convert critical path IDs to UUIDs (excluding virtual START and END)
    critical_path_uuids = [UUID(cid) for cid in critical_path]

    return {
        "nodes": formatted_nodes,
        "edges": edges,
        "critical_path": critical_path_uuids,
        "mode": project.mode,
        "duration": round(duration, 3) if is_pert else round(duration)
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
    available_time = None
    if project.target_completion_date is not None:
        start_date = project.created_at.date()
        target_time = float((project.target_completion_date - start_date).days)
        available_time = target_time

    nodes, critical_path, expected_duration, variance, probability = cpm_engine.calculate_pert(
        activities_data, target_time=target_time
    )

    return {
        "expected_project_duration": round(expected_duration, 3) if expected_duration is not None else None,
        "project_variance": round(variance, 3) if variance is not None else None,
        "standard_deviation": round(math.sqrt(variance), 3) if variance is not None else None,
        "probability": probability,
        "available_time": available_time,
        "target_completion_date": project.target_completion_date
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
    act_ids = [act.id for act in activities]
    
    deps_by_act: Dict[str, List[Dict]] = {}
    if act_ids:
        stmt = select(activity_dependencies).where(activity_dependencies.c.activity_id.in_(act_ids))
        dep_rows = db.execute(stmt).fetchall()
        for row in dep_rows:
            aid = str(row.activity_id)
            pid = str(row.predecessor_activity_id)
            dtype = getattr(row, 'dependency_type', 'FS') or 'FS'
            lag_val = getattr(row, 'lag', 0.0) or 0.0
            deps_by_act.setdefault(aid, []).append({
                "predecessor_id": pid,
                "dependency_type": str(dtype).upper(),
                "lag": float(lag_val)
            })

    activities_data = []
    for act in activities:
        aid_str = str(act.id)
        deps = deps_by_act.get(aid_str, [])
        pred_ids = [d["predecessor_id"] for d in deps] if deps else [str(pred.id) for pred in act.predecessors]
        activities_data.append({
            "id": aid_str,
            "name": act.name,
            "duration": act.duration,
            "optimistic_time": act.optimistic_time,
            "most_likely_time": act.most_likely_time,
            "pessimistic_time": act.pessimistic_time,
            "crash_duration": act.crash_duration,
            "normal_cost": act.normal_cost,
            "crash_cost": act.crash_cost,
            "category": act.category,
            "vendor_name": act.vendor_name,
            "is_milestone": act.is_milestone,
            "vendor_available_from": act.vendor_available_from,
            "vendor_available_to": act.vendor_available_to,
            "predecessor_ids": pred_ids,
            "dependencies": deps
        })
    return activities_data



def crash_project(db: Session, project_id: UUID, request: ProjectCrashRequest) -> Dict:
    project = get_project_or_404(db, project_id)
    activities_data = _prepare_cpm_input_from_db(db, project_id)
    
    result = cpm_engine.crash_project_network(
        activities_data,
        target_duration=request.target_duration,
        max_budget=request.max_budget
    )
    return result


def run_monte_carlo_simulation(db: Session, project_id: UUID, request: MonteCarloRequest) -> Dict:
    project = get_project_or_404(db, project_id)
    activities_data = _prepare_cpm_input_from_db(db, project_id)

    target_time = request.target_time
    if target_time is None and project.target_completion_date is not None and project.created_at is not None:
        start_date = project.created_at.date()
        target_time = float((project.target_completion_date - start_date).days)

    return cpm_engine.run_monte_carlo_simulation(
        activities_data,
        num_simulations=request.num_simulations,
        target_time=target_time
    )


def create_project_from_template(db: Session, template_name: str) -> Project:
    from app.services.event_templates import EVENT_TEMPLATES
    
    t_name = template_name.upper()
    if t_name not in EVENT_TEMPLATES:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{template_name}' not found. Available templates: {list(EVENT_TEMPLATES.keys())}"
        )

    t_data = EVENT_TEMPLATES[t_name]

    project = Project(
        name=t_data["name"],
        description=t_data["description"],
        category=t_data["category"],
        mode=t_data["mode"],
        start_date=date.today()
    )
    db.add(project)
    db.flush()

    created_activities: Dict[str, Activity] = {}
    
    for act_spec in t_data["activities"]:
        dur = act_spec.get("duration")
        if dur is None:
            dur = (act_spec["optimistic"] + 4 * act_spec["most_likely"] + act_spec["pessimistic"]) / 6.0

        activity = Activity(
            project_id=project.id,
            name=act_spec["name"],
            duration=dur,
            optimistic_time=act_spec.get("optimistic"),
            most_likely_time=act_spec.get("most_likely"),
            pessimistic_time=act_spec.get("pessimistic"),
            crash_duration=act_spec.get("crash_dur"),
            normal_cost=act_spec.get("normal_cost"),
            crash_cost=act_spec.get("crash_cost"),
            category=act_spec.get("category"),
            vendor_name=act_spec.get("vendor_name"),
            is_milestone=act_spec.get("is_milestone", False)
        )
        db.add(activity)
        db.flush()
        created_activities[act_spec["temp_key"]] = activity

    for act_spec in t_data["activities"]:
        act_obj = created_activities[act_spec["temp_key"]]
        preds = []
        for p_key in act_spec.get("preds", []):
            if p_key in created_activities:
                preds.append(created_activities[p_key])
        act_obj.predecessors = preds

    db.commit()
    db.refresh(project)
    return project


def check_vendor_availability(db: Session, project_id: UUID) -> Dict:
    from datetime import timedelta, date
    project = get_project_or_404(db, project_id)
    activities_data = _prepare_cpm_input_from_db(db, project_id)

    proj_start = project.start_date or date.today()


    if project.mode == "CPM":
        nodes, _, _ = cpm_engine.calculate_cpm(activities_data)
    else:
        nodes, _, _, _, _ = cpm_engine.calculate_pert(activities_data)

    activities_db = db.query(Activity).filter(Activity.project_id == project_id).all()
    act_map = {str(a.id): a for a in activities_db}

    conflicts = []

    node_schedules = {}
    for nid, node in nodes.items():
        if nid in ("START", "END"):
            continue
        sch_start = proj_start + timedelta(days=int(node.es))
        sch_finish = proj_start + timedelta(days=int(node.ef))
        node_schedules[nid] = {
            "node": node,
            "act_db": act_map.get(nid),
            "start": sch_start,
            "finish": sch_finish
        }

    for nid, item in node_schedules.items():
        act = item["act_db"]
        node = item["node"]
        sch_s = item["start"]
        sch_f = item["finish"]

        if act and act.vendor_name:
            v_from = act.vendor_available_from
            v_to = act.vendor_available_to

            is_violation = False
            rec = ""

            if v_from and sch_s < v_from:
                is_violation = True
                days_early = (v_from - sch_s).days
                if node.slack >= days_early:
                    rec = f"Activity starts {days_early} days before vendor is available. Consume {days_early} days of float (slack = {node.slack}d) to delay start."
                else:
                    rec = f"Activity starts {days_early} days before vendor is available, exceeding total float ({node.slack}d)."
            
            if v_to and sch_f > v_to:
                is_violation = True
                days_late = (sch_f - v_to).days
                rec = f"Activity finishes {days_late} days after vendor availability ends. Crash schedule or adjust window."

            if is_violation:
                conflicts.append({
                    "conflict_type": "VENDOR_AVAILABILITY_VIOLATION",
                    "activity_id": act.id,
                    "activity_name": act.name,
                    "vendor_name": act.vendor_name,
                    "scheduled_start": sch_s,
                    "scheduled_finish": sch_f,
                    "available_from": v_from,
                    "available_to": v_to,
                    "conflicting_activity_id": None,
                    "conflicting_activity_name": None,
                    "total_float": node.slack,
                    "resolution_recommendation": rec
                })

    vendor_groups = {}
    for nid, item in node_schedules.items():
        vname = item["act_db"].vendor_name if item["act_db"] else None
        if vname:
            vendor_groups.setdefault(vname, []).append(item)

    for vname, group in vendor_groups.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a1, a2 = group[i], group[j]
                overlap_start = max(a1["start"], a2["start"])
                overlap_finish = min(a1["finish"], a2["finish"])

                if overlap_start < overlap_finish:
                    conflicts.append({
                        "conflict_type": "VENDOR_OVERBOOKING",
                        "activity_id": a1["act_db"].id,
                        "activity_name": a1["act_db"].name,
                        "vendor_name": vname,
                        "scheduled_start": a1["start"],
                        "scheduled_finish": a1["finish"],
                        "available_from": a1["act_db"].vendor_available_from,
                        "available_to": a1["act_db"].vendor_available_to,
                        "conflicting_activity_id": a2["act_db"].id,
                        "conflicting_activity_name": a2["act_db"].name,
                        "total_float": a1["node"].slack,
                        "resolution_recommendation": f"Vendor '{vname}' is double-booked for '{a1['act_db'].name}' and '{a2['act_db'].name}' between {overlap_start} and {overlap_finish}."
                    })

    return {
        "project_id": project.id,
        "project_start_date": proj_start,
        "has_conflicts": len(conflicts) > 0,
        "total_conflicts": len(conflicts),
        "conflicts": conflicts
    }


# Function aliases for API router compatibility
simulate_project = simulate_change
run_monte_carlo = run_monte_carlo_simulation
get_project_network = compute_network
get_project_pert = compute_pert_analysis
