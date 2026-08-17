from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum
from app.schemas.activity import ActivityResponse

class ProjectMode(str, Enum):
    CPM = "CPM"
    PERT = "PERT"

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    target_completion_date: Optional[date] = None
    mode: ProjectMode

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    target_completion_date: Optional[date] = None
    mode: Optional[ProjectMode] = None

class ProjectResponse(ProjectBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ProjectWithActivitiesResponse(ProjectResponse):
    activities: List[ActivityResponse] = Field(default_factory=list)
