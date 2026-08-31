
import uuid
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import String, ForeignKey, Table, Column, DateTime, Date, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# Association table representing the many-to-many
# self-referencing activity dependencies with dependency types (FS, SS, FF, SF) and lag
activity_dependencies = Table(
    "activity_dependencies",
    Base.metadata,
    Column(
        "activity_id",
        ForeignKey("activities.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "predecessor_activity_id",
        ForeignKey("activities.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "dependency_type",
        String(10),
        default="FS",
        nullable=False,
    ),
    Column(
        "lag",
        Float,
        default=0.0,
        nullable=False,
    ),
)



class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    duration: Mapped[float] = mapped_column(
        default=0.0,
    )

    optimistic_time: Mapped[Optional[float]] = mapped_column(
        nullable=True,
    )

    most_likely_time: Mapped[Optional[float]] = mapped_column(
        nullable=True,
    )

    pessimistic_time: Mapped[Optional[float]] = mapped_column(
        nullable=True,
    )

    # Gap 2: Crashing / Optimization parameters
    crash_duration: Mapped[Optional[float]] = mapped_column(
        nullable=True,
    )

    normal_cost: Mapped[Optional[float]] = mapped_column(
        nullable=True,
    )

    crash_cost: Mapped[Optional[float]] = mapped_column(
        nullable=True,
    )

    # Gap 4: Event Domain Metadata
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    vendor_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    is_milestone: Mapped[bool] = mapped_column(
        default=False,
    )

    # Gap 5: Vendor / Resource Availability Constraints
    vendor_available_from: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )

    vendor_available_to: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="activities",
    )

    # Activities that this activity depends on
    predecessors: Mapped[List["Activity"]] = relationship(
        "Activity",
        secondary=activity_dependencies,
        primaryjoin="Activity.id == activity_dependencies.c.activity_id",
        secondaryjoin="Activity.id == activity_dependencies.c.predecessor_activity_id",
        back_populates="successors",
    )

    # Activities that depend on this activity
    successors: Mapped[List["Activity"]] = relationship(
        "Activity",
        secondary=activity_dependencies,
        primaryjoin="Activity.id == activity_dependencies.c.predecessor_activity_id",
        secondaryjoin="Activity.id == activity_dependencies.c.activity_id",
        back_populates="predecessors",
    )

    # Expose predecessor IDs for the API response.
    # This converts:
    #
    # activity.predecessors
    #
    # into:
    #
    # activity.predecessor_ids
    #
    @property
    def predecessor_ids(self) -> List[uuid.UUID]:
        return [predecessor.id for predecessor in self.predecessors]

    @property
    def dependencies(self) -> List[dict]:
        from sqlalchemy import select
        from sqlalchemy.orm import object_session
        session = object_session(self)
        if not session:
            return []
        stmt = select(activity_dependencies).where(activity_dependencies.c.activity_id == self.id)
        rows = session.execute(stmt).fetchall()
        result = []
        for r in rows:
            result.append({
                "predecessor_id": r.predecessor_activity_id,
                "dependency_type": getattr(r, 'dependency_type', 'FS') or 'FS',
                "lag": float(getattr(r, 'lag', 0.0) or 0.0)
            })
        return result

