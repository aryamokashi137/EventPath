from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class XaiEvidence(BaseModel):
    """A single auditable number behind a generated sentence."""
    label: str
    value: str


class XaiAction(BaseModel):
    """A recommendation derived from the explanation, with its justification."""
    priority: str = Field("MEDIUM", description="HIGH | MEDIUM | LOW")
    action: str
    rationale: str
    metric: str = ""


class XaiCard(BaseModel):
    """A themed block of explanation (bottleneck, merge bias, conflict...)."""
    severity: str = Field("INFO", description="CRITICAL | WARNING | INFO | SUCCESS")
    kind: str
    title: str
    narrative: str
    evidence: List[XaiEvidence] = Field(default_factory=list)
    actions: List[XaiAction] = Field(default_factory=list)
    activity_ids: List[str] = Field(default_factory=list)


class XaiHeadline(BaseModel):
    label: str
    value: str
    tone: str = "info"


class XaiEvidenceTrace(BaseModel):
    """Records which method produced which number, for auditability."""
    step: str
    method: str
    inputs: str = ""


class XaiConfidence(BaseModel):
    level: str = Field("LOW", description="HIGH | MEDIUM | LOW")
    basis: str


class XaiNarrative(BaseModel):
    """Fused multi-report summary used for the dynamic summary banner."""
    project_name: str
    narrative: List[str] = Field(default_factory=list)
    severity: str = "INFO"
    high_risk_findings: List[str] = Field(default_factory=list)
    recommended_actions: List[XaiAction] = Field(default_factory=list)


class XaiReport(BaseModel):
    """The uniform envelope shared by every XAI endpoint."""
    report_type: str
    title: str
    headline: XaiHeadline
    summary: str
    narrative: List[str] = Field(default_factory=list)
    cards: List[XaiCard] = Field(default_factory=list)
    severity: str = "INFO"
    high_risk_findings: List[str] = Field(default_factory=list)
    recommended_actions: List[XaiAction] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    evidence_trace: List[XaiEvidenceTrace] = Field(default_factory=list)
    confidence: XaiConfidence
    project_id: Optional[UUID] = None
    generated_at: Optional[str] = None


class CriticalPathExplanationResponse(XaiReport):
    report_type: str = "CRITICAL_PATH_FLOAT"


class RiskDiagnosticsRequest(BaseModel):
    num_simulations: int = Field(600, ge=100, le=10000,
                                 description="Monte Carlo trials used for the explanation (100 to 10000)")
    target_time: Optional[float] = Field(
        None, description="Committed duration in days; falls back to the project's target completion date")
    seed: int = Field(20260926, description="Random seed so the explanation is reproducible")
    near_critical_threshold: float = Field(
        0.30, gt=0.0, le=1.0,
        description="Simulated critical frequency above which an alternative path is reported as near-critical")
    deadline_buffer_percentile: int = Field(
        80, ge=50, le=99, description="Percentile recommended as the internal commitment date")
    include_monte_carlo: bool = Field(
        True, description="Run the seeded simulation that quantifies merge bias and hidden criticality")


class RiskDiagnosticsResponse(XaiReport):
    report_type: str = "PROBABILISTIC_RISK"
    merge_path_bias: List[Dict[str, Any]] = Field(
        default_factory=list, description="Raw merge-event metrics behind the generated narrative")
    path_statistics: Optional[Dict[str, Any]] = Field(
        None, description="Seeded simulation summary used as the evidence base")
    target_completion_date: Optional[date] = None
    project_start_date: Optional[date] = None


class CounterfactualCrashingRequest(BaseModel):
    target_duration: Optional[float] = Field(
        None, gt=0.0, description="Desired compressed duration in days; omitted means compress as far as possible")
    max_budget: Optional[float] = Field(
        None, ge=0.0, description="Maximum additional budget available for crashing")
    project_name: Optional[str] = Field(None, max_length=255)


class CounterfactualCrashingResponse(XaiReport):
    report_type: str = "COUNTERFACTUAL_CRASHING"
    crash_plan: Dict[str, Any] = Field(
        default_factory=dict, description="The raw crashing plan the explanation was generated from")


class VendorRecommendationsResponse(XaiReport):
    report_type: str = "VENDOR_CONFLICTS"
    project_start_date: Optional[date] = None
    conflict_count: int = 0


class XaiBundleResponse(BaseModel):
    """All four reports plus a fused narrative, for a single-page XAI view."""
    project_id: UUID
    project_name: str
    mode: str
    narrative: XaiNarrative
    critical_path: XaiReport
    risk: Optional[XaiReport] = None
    crashing: Optional[XaiReport] = None
    vendor: XaiReport
    generated_at: str
