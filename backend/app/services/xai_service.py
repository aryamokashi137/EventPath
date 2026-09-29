"""Database orchestration for the XAI explanation layer.

Resolves persisted project data into the raw metrics consumed by
:mod:`app.services.xai_engine` and assembles the API envelopes. All
statistical language is produced by the engine; this module only gathers
inputs, converts values to JSON-safe primitives and enforces HTTP semantics.
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import math

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.xai import (
    CounterfactualCrashingRequest,
    RiskDiagnosticsRequest,
)
from app.services import cpm_engine, project_service, xai_engine


def _project_start(project: Project) -> date:
    return project.start_date or (project.created_at.date() if project.created_at else date.today())


def _target_time(project: Project) -> Optional[float]:
    if project.target_completion_date is None:
        return None
    return float((project.target_completion_date - _project_start(project)).days)


def _load(db: Session, project_id: UUID) -> Tuple[Project, List[Dict[str, Any]]]:
    project = project_service.get_project_or_404(db, project_id)
    return project, project_service._prepare_cpm_input_from_db(db, project_id)


def _solve(project: Project, activities: List[Dict[str, Any]]):
    """Return (nodes, critical_path, duration, project_variance) for the project mode."""
    if project.mode == "CPM":
        nodes, critical_path, duration = cpm_engine.calculate_cpm(activities)
        return nodes, critical_path, duration, 0.0
    nodes, critical_path, expected, variance, _ = cpm_engine.calculate_pert(activities)
    return nodes, critical_path, expected, variance


def _envelope(report: Dict[str, Any], project: Project) -> Dict[str, Any]:
    report["project_id"] = project.id
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    return report


def _serialise_vendor_conflicts(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    conflicts: List[Dict[str, Any]] = []
    for row in raw.get("conflicts", []) or []:
        conflicts.append({
            "conflict_type": row.get("conflict_type"),
            "activity_id": str(row.get("activity_id")),
            "activity_name": row.get("activity_name"),
            "vendor_name": row.get("vendor_name"),
            "scheduled_start": row.get("scheduled_start"),
            "scheduled_finish": row.get("scheduled_finish"),
            "available_from": row.get("available_from"),
            "available_to": row.get("available_to"),
            "conflicting_activity_id": str(row.get("conflicting_activity_id"))
            if row.get("conflicting_activity_id") else None,
            "conflicting_activity_name": row.get("conflicting_activity_name"),
            "total_float": float(row.get("total_float", 0.0) or 0.0),
            "resolution_recommendation": row.get("resolution_recommendation", ""),
        })
    return conflicts


def get_critical_path_explanation(db: Session, project_id: UUID) -> Dict[str, Any]:
    """Deterministic CPM explanation: bottlenecks, zero float and buffer allocation."""
    project, activities = _load(db, project_id)
    if not activities:
        return _envelope(xai_engine.explain_critical_path_and_float(
            cpm_engine.build_network([]), [], 0.0, project.name, project.mode
        ), project)

    nodes, critical_path, duration, _ = _solve(project, activities)
    report = xai_engine.explain_critical_path_and_float(
        nodes, critical_path, duration, project.name, project.mode
    )
    return _envelope(report, project)


def get_risk_diagnostics(
    db: Session,
    project_id: UUID,
    request: Optional[RiskDiagnosticsRequest] = None,
) -> Dict[str, Any]:
    """Probabilistic risk explanation including merge-path bias detection."""
    request = request or RiskDiagnosticsRequest()
    project, activities = _load(db, project_id)

    if not activities:
        empty = cpm_engine.build_network([])
        report = xai_engine.explain_probabilistic_risk(
            empty, [], target_time=None, probability=None, expected_duration=0.0,
            project_variance=0.0, project_name=project.name, mode=project.mode,
            near_critical_threshold=request.near_critical_threshold,
            deadline_buffer_percentile=request.deadline_buffer_percentile,
        )
        payload = _envelope(report, project)
        payload["target_completion_date"] = project.target_completion_date
        payload["project_start_date"] = _project_start(project)
        return payload

    nodes, critical_path, expected, analytical_variance = _solve(project, activities)

    target_time = request.target_time if request.target_time is not None else _target_time(project)
    analytical_probability = None
    if project.mode == "PERT" and target_time is not None and analytical_variance > 0:
        z_score = (target_time - expected) / math.sqrt(analytical_variance)
        analytical_probability = xai_engine.standard_normal_cdf(z_score)

    path_statistics = None
    criticality_indices = None
    if request.include_monte_carlo:
        path_statistics = xai_engine.simulate_path_statistics(
            activities, num_simulations=request.num_simulations, seed=request.seed
        )
        criticality_indices = path_statistics.get("activity_criticality")

    merge_bias = xai_engine.detect_merge_path_bias(nodes)

    report = xai_engine.explain_probabilistic_risk(
        nodes,
        critical_path,
        target_time=target_time,
        probability=analytical_probability,
        expected_duration=expected,
        project_variance=analytical_variance,
        criticality_indices=criticality_indices,
        merge_event_bias=merge_bias,
        path_statistics=path_statistics,
        project_name=project.name,
        mode=project.mode,
        near_critical_threshold=request.near_critical_threshold,
        deadline_buffer_percentile=request.deadline_buffer_percentile,
    )

    payload = _envelope(report, project)
    payload["merge_path_bias"] = merge_bias
    payload["path_statistics"] = path_statistics
    payload["target_completion_date"] = project.target_completion_date
    payload["project_start_date"] = _project_start(project)
    return payload


def get_counterfactual_crashing(
    db: Session,
    project_id: UUID,
    request: Optional[CounterfactualCrashingRequest] = None,
) -> Dict[str, Any]:
    """Counterfactual trade-off narrative around the crashing optimisation."""
    request = request or CounterfactualCrashingRequest()
    project, activities = _load(db, project_id)

    if not activities:
        empty = cpm_engine.build_network([])
        report = xai_engine.explain_schedule_crashing([], 0.0, project_name=project.name)
        payload = _envelope(report, project)
        payload["crash_plan"] = {}
        return payload

    _, _, baseline, _ = _solve(project, activities)
    report = xai_engine.explain_schedule_crashing(
        activities,
        baseline,
        target_duration=request.target_duration,
        max_budget=request.max_budget,
        project_name=request.project_name or project.name,
    )
    plan = {
        "original_duration": report["metrics"].get("baseline_duration_days"),
        "crashed_duration": report["metrics"].get("crashed_duration_days"),
        "total_days_saved": report["metrics"].get("days_saved"),
        "additional_crash_cost": report["metrics"].get("additional_crash_cost"),
        "average_cost_per_day": report["metrics"].get("average_cost_per_day"),
        "crashed_activity_count": report["metrics"].get("crashed_activity_count"),
    }
    payload = _envelope(report, project)
    payload["crash_plan"] = plan
    return payload


def get_vendor_recommendations(db: Session, project_id: UUID) -> Dict[str, Any]:
    """Turn detected vendor collisions into float-shift recommendations."""
    project, activities = _load(db, project_id)
    start_date = _project_start(project)

    if not activities:
        raw = {"conflicts": []}
        nodes = cpm_engine.build_network([])
    else:
        raw = project_service.check_vendor_availability(db, project_id)
        nodes = _solve(project, activities)[0]

    report = xai_engine.explain_vendor_conflicts(
        _serialise_vendor_conflicts(raw),
        project_start_date=start_date,
        project_name=project.name,
        nodes=nodes,
    )
    payload = _envelope(report, project)
    payload["project_start_date"] = start_date
    payload["conflict_count"] = int(raw.get("total_conflicts", 0) or 0)
    return payload


def get_xai_bundle(
    db: Session,
    project_id: UUID,
    request: Optional[RiskDiagnosticsRequest] = None,
) -> Dict[str, Any]:
    """Fuse all four reports into a single payload for the summary banner."""
    project = project_service.get_project_or_404(db, project_id)

    reports = [get_critical_path_explanation(db, project_id)]
    try:
        reports.append(get_risk_diagnostics(db, project_id, request))
    except (ValueError, ArithmeticError):
        pass
    try:
        reports.append(get_vendor_recommendations(db, project_id))
    except HTTPException:
        raise

    narrative = xai_engine.build_narrative_summary(reports, project.name)
    return {
        "project_id": project.id,
        "project_name": project.name,
        "mode": project.mode,
        "narrative": narrative,
        "critical_path": reports[0],
        "risk": reports[1] if len(reports) > 1 else None,
        "crashing": None,
        "vendor": reports[2] if len(reports) > 2 else reports[-1],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def require_activities(db: Session, project_id: UUID) -> None:
    """Guard for endpoints that are meaningless on an empty network."""
    project = project_service.get_project_or_404(db, project_id)
    activities = project_service._prepare_cpm_input_from_db(db, project_id)
    if not activities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This project has no activities yet, so no explanation can be generated."
        )
