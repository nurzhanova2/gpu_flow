from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NodeStatus(str, Enum):
    healthy = "healthy"
    standby = "standby"
    degraded = "degraded"
    offline = "offline"


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"n_{uuid4().hex[:12]}")
    hostname: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    region: Mapped[str] = mapped_column(String(64), default="rack-a")
    gpu_model: Mapped[str] = mapped_column(String(64), default="T4")
    gpu_total: Mapped[int] = mapped_column(Integer, default=1)
    gpu_used: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[NodeStatus] = mapped_column(SqlEnum(NodeStatus), default=NodeStatus.healthy, index=True)

    cpu_usage: Mapped[int] = mapped_column(Integer, default=0)
    ram_usage: Mapped[int] = mapped_column(Integer, default=0)
    temperature: Mapped[int] = mapped_column(Integer, default=40)
    uptime_hours: Mapped[int] = mapped_column(Integer, default=0)

    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    sessions = relationship("Session", back_populates="node")
