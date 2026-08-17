from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

class SimulationRequest(BaseModel):
    activity_id: UUID = Field(..., description="ID of the activity to temporarily modify")
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    duration: Optional[float] = Field(None, description="Hypothetical duration")
    optimistic_time: Optional[float] = Field(None, description="Hypothetical optimistic time")
    most_likely_time: Optional[float] = Field(None, description="Hypothetical most likely time")
    pessimistic_time: Optional[float] = Field(None, description="Hypothetical pessimistic time")
    predecessor_ids: Optional[List[UUID]] = Field(None, description="Hypothetical predecessors")

    @model_validator(mode="after")
    def validate_estimates(self) -> "SimulationRequest":
        if self.duration is not None and self.duration <= 0:
            raise ValueError("Duration must be greater than zero.")
            
        opt, lk, pes = self.optimistic_time, self.most_likely_time, self.pessimistic_time
        # Check values are positive
        for val, name in [(opt, "optimistic"), (lk, "most_likely"), (pes, "pessimistic")]:
            if val is not None and val <= 0:
                raise ValueError(f"{name}_time must be greater than zero.")
                
        # If all three are provided, check order
        if opt is not None and lk is not None and pes is not None:
            if not (opt <= lk <= pes):
                raise ValueError("PERT estimates must follow: optimistic <= most_likely <= pessimistic")
        return self


class SimulationResponse(BaseModel):
    new_critical_path: List[UUID] = Field(..., description="New sequence of critical activity IDs")
    new_project_duration: float = Field(..., description="New project duration")
    new_completion_probability: Optional[float] = Field(None, description="New probability of on-time completion")
    flipped_to_critical: List[UUID] = Field(..., description="Activities that were non-critical but are now critical")
    flipped_to_non_critical: List[UUID] = Field(..., description="Activities that were critical but are now non-critical")
