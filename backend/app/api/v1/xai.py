from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.xai import (
    CounterfactualCrashingRequest,
    CounterfactualCrashingResponse,
    CriticalPathExplanationResponse,
    RiskDiagnosticsRequest,
    RiskDiagnosticsResponse,
    VendorRecommendationsResponse,
    XaiBundleResponse,
)
from app.services import xai_service


router = APIRouter(prefix="/projects", tags=["xai"])


@router.get(
    "/{project_id}/xai/critical-path-explanation",
    response_model=CriticalPathExplanationResponse,
    summary="Explain the critical path, zero-float bottlenecks and float allocation",
)
def get_critical_path_explanation(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """Deterministic XAI narrative for the CPM network.

    Turns ES/EF/LS/LF and the total/free float figures into bottleneck
    narratives, near-critical warnings and a float-shield map of the
    alternative routes through the network.
    """
    return xai_service.get_critical_path_explanation(db, project_id)


@router.post(
    "/{project_id}/xai/risk-diagnostics",
    response_model=RiskDiagnosticsResponse,
    summary="Explain completion probability, merge-path bias and hidden criticality",
)
def get_risk_diagnostics(
    project_id: UUID,
    risk_in: Optional[RiskDiagnosticsRequest] = None,
    db: Session = Depends(get_db)
):
    """Probabilistic XAI narrative backed by a seeded, reproducible simulation.

    Flags merge-path bias for parallel branches whose float is smaller than
    their combined duration variance, reports activities that the deterministic
    schedule hides, and recommends a percentile-based commitment date.
    """
    return xai_service.get_risk_diagnostics(db, project_id, risk_in)


@router.post(
    "/{project_id}/xai/counterfactual-crashing",
    response_model=CounterfactualCrashingResponse,
    summary="Explain the schedule crashing trade-off with counterfactual plans",
)
def get_counterfactual_crashing(
    project_id: UUID,
    crash_in: Optional[CounterfactualCrashingRequest] = None,
    db: Session = Depends(get_db)
):
    """Counterfactual XAI narrative for the crashing optimiser.

    Explains why the cheapest critical activities were compressed, why cheaper
    off-path activities were structurally excluded, and how much a feasible
    alternative plan would have cost.
    """
    return xai_service.get_counterfactual_crashing(db, project_id, crash_in)


@router.get(
    "/{project_id}/xai/vendor-recommendations",
    response_model=VendorRecommendationsResponse,
    summary="Translate vendor calendar collisions into float-shift advice",
)
def get_vendor_recommendations(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """Vendor constraint XAI narrative.

    For every double-booking or availability-window violation it reports the
    float-shift adjustment that resolves the clash at zero cost to the project
    date, and escalates the cases where float is insufficient.
    """
    return xai_service.get_vendor_recommendations(db, project_id)


@router.get(
    "/{project_id}/xai/bundle",
    response_model=XaiBundleResponse,
    summary="Fused XAI summary for the dynamic explanation banner",
)
def get_xai_bundle(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """Return every available XAI report plus a fused narrative in one call."""
    return xai_service.get_xai_bundle(db, project_id)
