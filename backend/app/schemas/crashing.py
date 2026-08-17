from typing import Optional, List, Dict
from uuid import UUID
from pydantic import BaseModel, Field

class ProjectCrashRequest(BaseModel):
    target_duration: Optional[float] = Field(None, description="Desired compressed project duration in days")
    max_budget: Optional[float] = Field(None, description="Maximum additional budget available for crashing")

class ActivityCrashDetail(BaseModel):
    activity_id: UUID
    activity_name: str
    original_duration: float
    crashed_duration: float
    days_crashed: float
    cost_per_day: float
    total_crash_cost: float

class ProjectCrashResponse(BaseModel):
    original_duration: float
    crashed_duration: float
    total_days_saved: float
    baseline_cost: float
    additional_crash_cost: float
    final_total_cost: float
    crashed_activities: List[ActivityCrashDetail]
    final_critical_path: List[UUID]
