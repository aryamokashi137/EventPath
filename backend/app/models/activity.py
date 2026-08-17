import uuid
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, ForeignKey, Table, Column, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

# Association table representing the many-to-many self-referencing dependencies
activity_dependencies = Table(
    "activity_dependencies",
    Base.metadata,
    Column(
        "activity_id", 
        ForeignKey("activities.id", ondelete="CASCADE"), 
        primary_key=True
    ),
    Column(
        "predecessor_activity_id", 
        ForeignKey("activities.id", ondelete="CASCADE"), 
        primary_key=True
    ),
)

class Activity(Base):
    __tablename__ = "activities"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), 
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    duration: Mapped[float] = mapped_column(default=0.0)
    optimistic_time: Mapped[Optional[float]] = mapped_column(nullable=True)
    most_likely_time: Mapped[Optional[float]] = mapped_column(nullable=True)
    pessimistic_time: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Gap 2: Crashing / Optimization parameters
    crash_duration: Mapped[Optional[float]] = mapped_column(nullable=True)
    normal_cost: Mapped[Optional[float]] = mapped_column(nullable=True)
    crash_cost: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Gap 4: Event Domain Metadata
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., VENUE, CATERING, AUDIO_VISUAL
    vendor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_milestone: Mapped[bool] = mapped_column(default=False)
    
    # Gap 5: Vendor / Resource Availability Constraints
    vendor_available_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    vendor_available_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow
    )
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="activities")
    
    predecessors: Mapped[List["Activity"]] = relationship(
        "Activity",
        secondary=activity_dependencies,
        primaryjoin="Activity.id == activity_dependencies.c.activity_id",
        secondaryjoin="Activity.id == activity_dependencies.c.predecessor_activity_id",
        back_populates="successors"
    )
    
    successors: Mapped[List["Activity"]] = relationship(
        "Activity",
        secondary=activity_dependencies,
        primaryjoin="Activity.id == activity_dependencies.c.predecessor_activity_id",
        secondaryjoin="Activity.id == activity_dependencies.c.activity_id",
        back_populates="predecessors"
    )
