from typing import Optional, List
from uuid import UUID
from datetime import date
from pydantic import BaseModel, Field

class ResourceConflict(BaseModel):
    conflict_type: str = Field(..., description="VENDOR_AVAILABILITY_VIOLATION | VENDOR_OVERBOOKING")
    activity_id: UUID
    activity_name: str
    vendor_name: Optional[str]
    scheduled_start: date
    scheduled_finish: date
    available_from: Optional[date]
    available_to: Optional[date]
    conflicting_activity_id: Optional[UUID] = None
    conflicting_activity_name: Optional[str] = None
    total_float: float
    resolution_recommendation: str

class AvailabilityCheckResponse(BaseModel):
    project_id: UUID
    project_start_date: date
    has_conflicts: bool
    total_conflicts: int
    conflicts: List[ResourceConflict]
