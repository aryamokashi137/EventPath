import uuid
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Text, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_completion_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="GENERAL")
    mode: Mapped[str] = mapped_column(String(10), nullable=False)  # "CPM" | "PERT"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationship to activities
    activities: Mapped[List["Activity"]] = relationship(
        "Activity",
        back_populates="project",
        cascade="all, delete-orphan"
    )

