from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QueueStatus(str, Enum):
    waiting = "waiting"
    starting = "starting"
    running = "running"
    failed = "failed"
    cancelled = "cancelled"


class LaunchProfile(Base):
    __tablename__ = "launch_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    label: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(255))
    queue_hint: Mapped[str] = mapped_column(String(64), default="~5 мин")
    tag: Mapped[str] = mapped_column(String(64), default="")
    icon: Mapped[str] = mapped_column(String(32), default="GPU")
    recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    gpu_count: Mapped[int] = mapped_column(Integer, default=1)
    memory_gb: Mapped[int] = mapped_column(Integer, default=16)
    cpu_cores: Mapped[int] = mapped_column(Integer, default=4)

    queue_items = relationship("QueueItem", back_populates="profile")
    sessions = relationship("Session", back_populates="profile")


class QueueItem(Base):
    __tablename__ = "queue_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"q_{uuid4().hex[:12]}")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("launch_profiles.id"), index=True)

    status: Mapped[QueueStatus] = mapped_column(SqlEnum(QueueStatus), default=QueueStatus.waiting, index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    status_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    queue_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eta_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    node_target: Mapped[str | None] = mapped_column(String(120), nullable=True)
    slurm_job_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    relaunch_from_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user = relationship("User", back_populates="queue_items")
    profile = relationship("LaunchProfile", back_populates="queue_items")
    session = relationship("Session", back_populates="queue_item", uselist=False)
