from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SessionStatus(str, Enum):
    starting = "starting"
    running = "running"
    idle = "idle"
    completed = "completed"
    failed = "failed"
    terminating = "terminating"
    terminated = "terminated"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"s_{uuid4().hex[:12]}")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("launch_profiles.id"), index=True)
    queue_item_id: Mapped[str | None] = mapped_column(ForeignKey("queue_items.id", ondelete="SET NULL"), nullable=True, unique=True)
    node_id: Mapped[str | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[SessionStatus] = mapped_column(SqlEnum(SessionStatus), default=SessionStatus.starting, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idle_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    slurm_job_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    jupyter_server_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notebook_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    gpu_usage: Mapped[float] = mapped_column(Float, default=0)
    memory_usage: Mapped[float] = mapped_column(Float, default=0)
    cpu_usage: Mapped[float] = mapped_column(Float, default=0)

    termination_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="sessions")
    profile = relationship("LaunchProfile", back_populates="sessions")
    node = relationship("Node", back_populates="sessions")
    queue_item = relationship("QueueItem", back_populates="session", uselist=False, foreign_keys=[queue_item_id])
