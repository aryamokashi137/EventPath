from typing import Optional, List, Dict
from uuid import UUID
from pydantic import BaseModel, Field

class MonteCarloRequest(BaseModel):
    num_simulations: int = Field(1000, ge=100, le=10000, description="Number of simulation runs (100 to 10000)")
    target_time: Optional[float] = Field(None, description="Optional target completion duration in days")

class SCurvePoint(BaseModel):
    duration: float
    cumulative_probability: float

class ActivityCriticalityIndex(BaseModel):
    activity_id: UUID
    activity_name: str
    criticality_percentage: float

class MonteCarloResponse(BaseModel):
    num_simulations: int
    mean_duration: float
    std_dev_duration: float
    min_duration: float
    max_duration: float
    p10: float
    p50: float
    p80: float
    p90: float
    p95: float
    empirical_probability: Optional[float]
    criticality_indices: List[ActivityCriticalityIndex]
    s_curve: List[SCurvePoint]
