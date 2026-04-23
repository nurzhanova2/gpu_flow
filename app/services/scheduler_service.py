from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.core.realtime import RealtimeManager
from app.integrations.jupyterhub.base import JupyterHubAdapter
from app.integrations.slurm.base import SlurmAdapter
from app.models import Alert, AlertLevel, AuditLog, LaunchProfile, Node, QueueItem, QueueStatus, Session, SessionStatus
from app.repositories.node_repo import NodeRepository
from app.repositories.queue_repo import QueueRepository


class SchedulerService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        realtime: RealtimeManager,
        slurm_adapter: SlurmAdapter,
        jupyterhub_adapter: JupyterHubAdapter,
    ) -> None:
        self.db = db
        self.settings = settings
        self.realtime = realtime
        self.slurm_adapter = slurm_adapter
        self.jupyterhub_adapter = jupyterhub_adapter
        self.queue_repo = QueueRepository(db)
        self.node_repo = NodeRepository(db)

    async def process_queue_tick(self) -> None:
        now = datetime.now(UTC)
        events: list[tuple[str, dict, str | None]] = []

        waiting_items = await self._load_waiting_items_for_processing()
        for item in waiting_items:
            if item.user.is_blocked:
                item.status = QueueStatus.cancelled
                item.status_updated_at = now
                item.is_archived = True
                events.append(("queue.updated", {"id": item.id, "status": item.status.value}, item.user_id))
                continue

            node = await self.node_repo.reserve_available_node(item.profile.gpu_count)
            if not node:
                continue

            submit_result = await self.slurm_adapter.submit_job(item.id, item.profile_id, item.user_id)
            session = Session(
                user_id=item.user_id,
                profile_id=item.profile_id,
                queue_item_id=item.id,
                node_id=node.id,
                status=SessionStatus.starting,
                status_updated_at=now,
                slurm_job_id=submit_result["job_id"],
                last_activity_at=now,
            )
            self.db.add(session)
            await self.db.flush()

            item.status = QueueStatus.starting
            item.status_updated_at = now
            item.node_target = node.hostname
            item.slurm_job_id = submit_result["job_id"]
            item.queue_position = 0
            item.eta_seconds = 0

            events.append(("queue.updated", {"id": item.id, "status": item.status.value, "nodeTarget": node.hostname}, item.user_id))
            events.append(("session.updated", {"id": session.id, "status": session.status.value, "userId": session.user_id}, session.user_id))

        starting_items = await self._load_starting_items_for_processing()
        for item in starting_items:
            if not item.session:
                continue
            elapsed = (now - item.status_updated_at).total_seconds()
            if elapsed < self.settings.queue_start_delay_seconds:
                continue

            slurm_status = await self.slurm_adapter.get_status(item.slurm_job_id or "")
            if slurm_status == "FAILED":
                await self._mark_startup_failed(item, item.session, now)
                events.append(("queue.updated", {"id": item.id, "status": item.status.value}, item.user_id))
                events.append(("session.updated", {"id": item.session.id, "status": item.session.status.value}, item.user_id))
                continue

            if slurm_status != "RUNNING":
                if elapsed >= self.settings.queue_start_timeout_seconds:
                    await self._mark_startup_failed(item, item.session, now)
                    item.failure_reason = "Slurm job startup timeout"
                    events.append(("queue.updated", {"id": item.id, "status": item.status.value}, item.user_id))
                    events.append(("session.updated", {"id": item.session.id, "status": item.session.status.value}, item.user_id))
                continue

            server_info = await self.jupyterhub_adapter.start_server(item.user_id, item.session.id)
            notebook_url = server_info.get("url")
            if not self._is_safe_notebook_url(notebook_url):
                await self._mark_startup_failed(
                    item,
                    item.session,
                    now,
                    failure_reason="Invalid notebook URL returned by JupyterHub adapter",
                    session_reason="invalid_notebook_url",
                )
                events.append(("queue.updated", {"id": item.id, "status": item.status.value}, item.user_id))
                events.append(("session.updated", {"id": item.session.id, "status": item.session.status.value}, item.user_id))
                continue

            item.status = QueueStatus.running
            item.status_updated_at = now

            item.session.status = SessionStatus.running
            item.session.started_at = item.session.started_at or now
            item.session.status_updated_at = now
            item.session.last_activity_at = now
            item.session.jupyter_server_id = server_info["server_id"]
            item.session.notebook_url = notebook_url

            events.append(("queue.updated", {"id": item.id, "status": item.status.value}, item.user_id))
            events.append(
                (
                    "session.updated",
                    {"id": item.session.id, "status": item.session.status.value, "notebookUrl": item.session.notebook_url},
                    item.user_id,
                )
            )

        await self._recalculate_waiting_positions()
        await self.db.commit()

        for event, payload, user_id in events:
            if user_id:
                await self.realtime.publish_admin_and_user(event, payload, user_id=user_id)
            else:
                await self.realtime.publish_admin(event, payload)
        await self._publish_waiting_positions()

    async def _mark_startup_failed(
        self,
        queue_item: QueueItem,
        session: Session,
        now: datetime,
        failure_reason: str = "Slurm job startup failed",
        session_reason: str = "slurm_failed",
    ) -> None:
        queue_item.status = QueueStatus.failed
        queue_item.failure_reason = failure_reason
        queue_item.status_updated_at = now
        queue_item.is_archived = True

        session.status = SessionStatus.failed
        session.termination_reason = session_reason
        session.status_updated_at = now
        session.ended_at = now

        if session.node_id:
            node = await self.db.get(Node, session.node_id)
            if node:
                profile = await self.db.get(LaunchProfile, session.profile_id)
                gpu_count = profile.gpu_count if profile else 1
                node.gpu_used = max(node.gpu_used - gpu_count, 0)

        self.db.add(
            Alert(
                level=AlertLevel.warning,
                message=f"Не удалось запустить сессию для пользователя {queue_item.user.username}: {failure_reason}",
            )
        )
        self.db.add(
            AuditLog(
                actor_user_id=None,
                action="scheduler.startup_failed",
                entity_type="queue",
                entity_id=queue_item.id,
                meta={"session_id": session.id},
            )
        )

    @staticmethod
    def _is_safe_notebook_url(url: str | None) -> bool:
        if not url:
            return False
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    async def _recalculate_waiting_positions(self) -> None:
        waiting_items = await self.queue_repo.list_waiting()
        slot_seconds = max(60, self.settings.queue_start_delay_seconds + 120)
        for idx, item in enumerate(waiting_items, start=1):
            item.queue_position = idx
            item.eta_seconds = slot_seconds * idx

    async def _publish_waiting_positions(self) -> None:
        waiting_items = await self.queue_repo.list_waiting()
        for item in waiting_items:
            await self.realtime.publish_admin_and_user(
                "queue.updated",
                {"id": item.id, "status": item.status.value, "queuePosition": item.queue_position, "etaSeconds": item.eta_seconds},
                user_id=item.user_id,
            )

    def _is_postgres(self) -> bool:
        bind = self.db.get_bind()
        return bind is not None and bind.dialect.name == "postgresql"

    async def _load_waiting_items_for_processing(self) -> list[QueueItem]:
        query = (
            select(QueueItem)
            .where(QueueItem.status == QueueStatus.waiting, QueueItem.is_archived.is_(False))
            .options(selectinload(QueueItem.user), selectinload(QueueItem.profile), selectinload(QueueItem.session))
            .order_by(QueueItem.priority.desc(), QueueItem.requested_at.asc())
        )
        if self._is_postgres():
            query = query.with_for_update(skip_locked=True)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _load_starting_items_for_processing(self) -> list[QueueItem]:
        query = (
            select(QueueItem)
            .where(QueueItem.status == QueueStatus.starting, QueueItem.is_archived.is_(False))
            .options(selectinload(QueueItem.session), selectinload(QueueItem.user), selectinload(QueueItem.profile))
            .order_by(QueueItem.status_updated_at.asc())
        )
        if self._is_postgres():
            query = query.with_for_update(skip_locked=True)
        result = await self.db.execute(query)
        return list(result.scalars().all())
