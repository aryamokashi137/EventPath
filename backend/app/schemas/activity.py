from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

class ActivityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    duration: float = Field(0.0, description="Duration in CPM mode.")
    optimistic_time: Optional[float] = Field(None, description="Optimistic time for PERT.")
    most_likely_time: Optional[float] = Field(None, description="Most likely time for PERT.")
    pessimistic_time: Optional[float] = Field(None, description="Pessimistic time for PERT.")
    predecessor_ids: List[UUID] = Field(default_factory=list, description="IDs of activities that this activity depends on.")

    @model_validator(mode="after")
    def validate_estimates(self) -> "ActivityCreate":
        # If no PERT times are set, check duration
        opt, lk, pes = self.optimistic_time, self.most_likely_time, self.pessimistic_time
        if opt is None and lk is None and pes is None:
            if self.duration <= 0:
                raise ValueError("Duration must be greater than zero.")
        else:
            # If any PERT estimate is set, all must be set
            if opt is None or lk is None or pes is None:
                raise ValueError("All three PERT estimates (optimistic, most_likely, pessimistic) must be provided.")
            if opt <= 0 or lk <= 0 or pes <= 0:
                raise ValueError("PERT estimates must be greater than zero.")
            if not (opt <= lk <= pes):
                raise ValueError("PERT estimates must follow: optimistic <= most_likely <= pessimistic")
        return self


class ActivityUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    duration: Optional[float] = None
    optimistic_time: Optional[float] = None
    most_likely_time: Optional[float] = None
    pessimistic_time: Optional[float] = None
    predecessor_ids: Optional[List[UUID]] = None

    @model_validator(mode="after")
    def validate_estimates(self) -> "ActivityUpdate":
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


class ActivityResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    duration: float
    optimistic_time: Optional[float] = None
    most_likely_time: Optional[float] = None
    pessimistic_time: Optional[float] = None
    created_at: datetime
    predecessor_ids: List[UUID] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
