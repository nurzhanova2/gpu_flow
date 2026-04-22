from __future__ import annotations

from datetime import UTC, datetime
from random import randint, random
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.core.realtime import RealtimeManager
from app.integrations.jupyterhub.base import JupyterHubAdapter
from app.integrations.metrics.base import MetricsAdapter
from app.integrations.slurm.base import SlurmAdapter
from app.models import Alert, AlertLevel, AuditLog, LaunchProfile, Node, QueueItem, Session, SessionStatus, User
from app.repositories.node_repo import NodeRepository
from app.repositories.session_repo import SessionRepository
from app.services.queue_service import QueueService


class SessionService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        realtime: RealtimeManager,
        slurm_adapter: SlurmAdapter,
        jupyterhub_adapter: JupyterHubAdapter,
        metrics_adapter: MetricsAdapter,
    ) -> None:
        self.db = db
        self.settings = settings
        self.realtime = realtime
        self.slurm_adapter = slurm_adapter
        self.jupyterhub_adapter = jupyterhub_adapter
        self.metrics_adapter = metrics_adapter
        self.session_repo = SessionRepository(db)
        self.node_repo = NodeRepository(db)

    async def relaunch(self, actor: User, session_id: str) -> tuple[str, str, int, int]:
        session = await self.db.scalar(select(Session).where(Session.id == session_id).options(selectinload(Session.user)))
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "SESSION_NOT_FOUND", "message": "Session not found", "details": {}}},
            )

        if actor.role.value != "admin" and session.user_id != actor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Cannot relaunch this session", "details": {}}},
            )

        target_user = session.user if actor.role.value == "admin" else actor
        queue_service = QueueService(self.db, self.settings, self.realtime, self.slurm_adapter)
        item, position, eta_min = await queue_service.enqueue(target_user, session.profile_id, relaunch_from_session_id=session.id)
        return item.id, item.status.value, position, eta_min

    async def get_access(self, actor: User, session_id: str, is_admin: bool = False) -> Session:
        session = await self.db.scalar(select(Session).where(Session.id == session_id).options(selectinload(Session.user)))
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "SESSION_NOT_FOUND", "message": "Session not found", "details": {}}},
            )

        if not is_admin and session.user_id != actor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Cannot access this session", "details": {}}},
            )
        if session.notebook_url and not self._is_safe_notebook_url(session.notebook_url):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error": {
                        "code": "NOTEBOOK_URL_INVALID",
                        "message": "Notebook URL is invalid",
                        "details": {},
                    }
                },
            )
        return session

    async def terminate(self, actor: User, session_id: str, is_admin: bool = False, reason: str = "manual_terminate") -> Session:
        session = await self.db.scalar(select(Session).where(Session.id == session_id))
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "SESSION_NOT_FOUND", "message": "Session not found", "details": {}}},
            )

        if not is_admin and session.user_id != actor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Cannot terminate this session", "details": {}}},
            )

        session.status = SessionStatus.terminating
        session.status_updated_at = datetime.now(UTC)
        session.termination_reason = reason

        self.db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="session.terminate",
                entity_type="session",
                entity_id=session.id,
                meta={"admin": is_admin, "reason": reason},
            )
        )
        await self.db.commit()

        await self.realtime.publish_admin_and_user(
            "session.updated",
            {"id": session.id, "status": session.status.value},
            user_id=session.user_id,
        )
        return session

    async def warn(self, actor: User, session_id: str, message: str) -> Session:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "SESSION_NOT_FOUND", "message": "Session not found", "details": {}}},
            )

        self.db.add(Alert(level=AlertLevel.warning, message=f"Session {session.id}: {message}"))
        self.db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="session.warn",
                entity_type="session",
                entity_id=session.id,
                meta={"message": message},
            )
        )
        await self.db.commit()
        await self.realtime.publish_admin_and_user(
            "session.updated",
            {"id": session.id, "warning": message, "status": session.status.value},
            user_id=session.user_id,
        )
        return session

    async def process_session_tick(self) -> None:
        now = datetime.now(UTC)
        admin_events: list[tuple[str, dict]] = []
        scoped_events: list[tuple[str, dict, str]] = []

        nodes = await self.node_repo.list_nodes()
        node_metrics = await self.metrics_adapter.get_nodes(len(nodes))
        for node, metric in zip(nodes, node_metrics):
            node.cpu_usage = metric["cpu"]
            node.ram_usage = metric["ram"]
            node.temperature = metric["temperature"]
            node.uptime_hours += metric["uptimeIncrement"]
            admin_events.append(("node.updated", {"id": node.id, "cpu": node.cpu_usage, "ram": node.ram_usage, "status": node.status.value}))

        active_sessions = await self.session_repo.list_active()
        for session in active_sessions:
            runtime_seconds = 0
            if session.started_at:
                runtime_seconds = int((now - session.started_at).total_seconds())

            if session.status == SessionStatus.running:
                session.gpu_usage = randint(55, 96)
                session.memory_usage = randint(44, 91)
                session.cpu_usage = randint(20, 83)

                if random() < 0.12:
                    session.status = SessionStatus.idle
                    session.idle_since = now
                    session.status_updated_at = now
                else:
                    session.last_activity_at = now

                if runtime_seconds > self.settings.session_max_runtime_seconds:
                    session.status = SessionStatus.terminating
                    session.status_updated_at = now
                    session.termination_reason = "max_runtime_exceeded"

            elif session.status == SessionStatus.idle:
                session.gpu_usage = randint(1, 15)
                session.memory_usage = randint(20, 40)
                session.cpu_usage = randint(5, 24)

                idle_seconds = int((now - (session.idle_since or now)).total_seconds())
                if random() < 0.3 and idle_seconds < self.settings.session_idle_timeout_seconds:
                    session.status = SessionStatus.running
                    session.idle_since = None
                    session.last_activity_at = now
                    session.status_updated_at = now
                elif idle_seconds >= self.settings.session_idle_timeout_seconds:
                    session.status = SessionStatus.terminating
                    session.status_updated_at = now
                    session.termination_reason = "idle_timeout"

                if runtime_seconds > self.settings.session_max_runtime_seconds:
                    session.status = SessionStatus.terminating
                    session.status_updated_at = now
                    session.termination_reason = "max_runtime_exceeded"

            if session.status == SessionStatus.terminating:
                elapsed = int((now - session.status_updated_at).total_seconds())
                if elapsed >= 10:
                    archived_queue_id = await self._finalize_termination(session, now)
                    if archived_queue_id:
                        scoped_events.append(("queue.updated", {"id": archived_queue_id, "archived": True}, session.user_id))

            if session.status in [SessionStatus.running, SessionStatus.idle] and runtime_seconds > 300 and random() < 0.02:
                archived_queue_id = await self._finalize_completion(session, now)
                if archived_queue_id:
                    scoped_events.append(("queue.updated", {"id": archived_queue_id, "archived": True}, session.user_id))

            scoped_events.append(
                (
                    "session.updated",
                    {
                        "id": session.id,
                        "status": session.status.value,
                        "gpuUsage": round(session.gpu_usage, 1),
                        "memoryUsage": round(session.memory_usage, 1),
                        "cpuUsage": round(session.cpu_usage, 1),
                    },
                    session.user_id,
                )
            )

        await self.db.commit()

        for event, payload in admin_events:
            await self.realtime.publish_admin(event, payload)
        for event, payload, user_id in scoped_events:
            await self.realtime.publish_admin_and_user(event, payload, user_id=user_id)

    async def _finalize_termination(self, session: Session, now: datetime) -> str | None:
        if session.jupyter_server_id:
            await self.jupyterhub_adapter.stop_server(session.jupyter_server_id)
        if session.slurm_job_id:
            await self.slurm_adapter.cancel_job(session.slurm_job_id)

        session.status = SessionStatus.terminated
        session.status_updated_at = now
        session.ended_at = now

        queue_item = await self.db.scalar(select(QueueItem).where(QueueItem.id == session.queue_item_id))
        if queue_item:
            queue_item.is_archived = True

        await self._release_node_gpu(session)
        return queue_item.id if queue_item else None

    async def _finalize_completion(self, session: Session, now: datetime) -> str | None:
        if session.jupyter_server_id:
            await self.jupyterhub_adapter.stop_server(session.jupyter_server_id)

        session.status = SessionStatus.completed
        session.status_updated_at = now
        session.ended_at = now

        queue_item = await self.db.scalar(select(QueueItem).where(QueueItem.id == session.queue_item_id))
        if queue_item:
            queue_item.is_archived = True

        await self._release_node_gpu(session)
        return queue_item.id if queue_item else None

    async def _release_node_gpu(self, session: Session) -> None:
        if not session.node_id:
            return
        node = await self.db.get(Node, session.node_id)
        if not node:
            return

        profile = await self.db.get(LaunchProfile, session.profile_id)
        profile_gpu = profile.gpu_count if profile else 1
        node.gpu_used = max(node.gpu_used - profile_gpu, 0)

    @staticmethod
    def _is_safe_notebook_url(url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
