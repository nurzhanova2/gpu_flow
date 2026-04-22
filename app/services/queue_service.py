from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.realtime import RealtimeManager
from app.integrations.slurm.base import SlurmAdapter
from app.models import AuditLog, LaunchProfile, QueueItem, QueueStatus, Session, SessionStatus, User
from app.repositories.queue_repo import QueueRepository
from app.repositories.session_repo import SessionRepository


class QueueService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        realtime: RealtimeManager,
        slurm_adapter: SlurmAdapter,
    ) -> None:
        self.db = db
        self.settings = settings
        self.realtime = realtime
        self.slurm_adapter = slurm_adapter
        self.queue_repo = QueueRepository(db)
        self.session_repo = SessionRepository(db)

    async def enqueue(self, user: User, profile_id: str, relaunch_from_session_id: str | None = None) -> tuple[QueueItem, int, int]:
        if user.is_blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "USER_BLOCKED", "message": "User is blocked", "details": {}}},
            )

        active_sessions = await self.session_repo.count_user_active_sessions(user.id)
        if active_sessions >= user.max_active_sessions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "ACTIVE_SESSION_LIMIT_REACHED",
                        "message": "Active session limit reached",
                        "details": {"max": user.max_active_sessions},
                    }
                },
            )

        queued_count = await self.queue_repo.count_user_active_queue(user.id)
        if queued_count >= user.max_queued_requests:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "QUEUE_LIMIT_REACHED",
                        "message": "Queued request limit reached",
                        "details": {"max": user.max_queued_requests},
                    }
                },
            )

        profile = await self.db.get(LaunchProfile, profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "LAUNCH_PROFILE_NOT_FOUND", "message": "Launch profile not found", "details": {}}},
            )

        item = QueueItem(user_id=user.id, profile_id=profile_id, status=QueueStatus.waiting, relaunch_from_session_id=relaunch_from_session_id)
        await self.queue_repo.create(item)
        await self._recalculate_waiting_positions()

        self.db.add(AuditLog(actor_user_id=user.id, action="queue.enqueue", entity_type="queue", entity_id=item.id, meta={"profile_id": profile_id}))
        await self.db.commit()

        await self.realtime.publish_admin_and_user(
            "queue.updated",
            {"id": item.id, "status": item.status.value, "queuePosition": item.queue_position, "etaSeconds": item.eta_seconds},
            user_id=item.user_id,
        )
        await self._publish_waiting_positions()
        return item, item.queue_position or 1, int((item.eta_seconds or 60) / 60)

    async def cancel(self, actor: User, queue_id: str, is_admin: bool = False) -> QueueItem:
        item = await self.queue_repo.get_by_id(queue_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "QUEUE_ITEM_NOT_FOUND", "message": "Queue item not found", "details": {}}},
            )

        if not is_admin and item.user_id != actor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Cannot access this queue item", "details": {}}},
            )

        now = datetime.now(UTC)
        if item.slurm_job_id:
            await self.slurm_adapter.cancel_job(item.slurm_job_id)

        linked_session = await self.db.scalar(select(Session).where(Session.queue_item_id == item.id))
        if linked_session and linked_session.status in [SessionStatus.starting, SessionStatus.running, SessionStatus.idle]:
            linked_session.status = SessionStatus.terminating
            linked_session.status_updated_at = now
            linked_session.termination_reason = "cancelled_by_user" if not is_admin else "cancelled_by_admin"

        item.status = QueueStatus.cancelled
        item.status_updated_at = now
        item.is_archived = True

        self.db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="queue.cancel",
                entity_type="queue",
                entity_id=item.id,
                meta={"admin": is_admin},
            )
        )

        await self._recalculate_waiting_positions()
        await self.db.commit()

        await self.realtime.publish_admin_and_user("queue.updated", {"id": item.id, "status": item.status.value}, user_id=item.user_id)
        if linked_session:
            await self.realtime.publish_admin_and_user(
                "session.updated",
                {"id": linked_session.id, "status": linked_session.status.value},
                user_id=linked_session.user_id,
            )
        await self._publish_waiting_positions()
        return item

    async def promote(self, actor: User, queue_id: str) -> QueueItem:
        item = await self.queue_repo.get_by_id(queue_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "QUEUE_ITEM_NOT_FOUND", "message": "Queue item not found", "details": {}}},
            )

        item.priority += 1
        await self._recalculate_waiting_positions()
        self.db.add(AuditLog(actor_user_id=actor.id, action="queue.promote", entity_type="queue", entity_id=item.id, meta={"priority": item.priority}))
        await self.db.commit()

        await self.realtime.publish_admin_and_user(
            "queue.updated",
            {"id": item.id, "status": item.status.value, "priority": item.priority},
            user_id=item.user_id,
        )
        await self._publish_waiting_positions()
        return item

    async def delete(self, actor: User, queue_id: str) -> QueueItem:
        item = await self.queue_repo.get_by_id(queue_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "QUEUE_ITEM_NOT_FOUND", "message": "Queue item not found", "details": {}}},
            )

        if item.slurm_job_id:
            await self.slurm_adapter.cancel_job(item.slurm_job_id)

        item.is_archived = True
        item.status = QueueStatus.cancelled
        item.status_updated_at = datetime.now(UTC)

        self.db.add(AuditLog(actor_user_id=actor.id, action="queue.delete", entity_type="queue", entity_id=item.id, meta={}))
        await self._recalculate_waiting_positions()
        await self.db.commit()

        await self.realtime.publish_admin_and_user(
            "queue.updated",
            {"id": item.id, "status": item.status.value, "archived": True},
            user_id=item.user_id,
        )
        await self._publish_waiting_positions()
        return item

    async def _recalculate_waiting_positions(self) -> None:
        waiting_items = await self.queue_repo.list_waiting()
        slot_seconds = max(60, self.settings.queue_start_delay_seconds + 120)

        for idx, item in enumerate(waiting_items, start=1):
            item.queue_position = idx
            item.eta_seconds = slot_seconds * idx

        active_items = await self.queue_repo.list_active()
        for item in active_items:
            if item.status in [QueueStatus.starting, QueueStatus.running]:
                item.queue_position = 0
                item.eta_seconds = 0

    async def _publish_waiting_positions(self) -> None:
        waiting_items = await self.queue_repo.list_waiting()
        for item in waiting_items:
            await self.realtime.publish_admin_and_user(
                "queue.updated",
                {"id": item.id, "status": item.status.value, "queuePosition": item.queue_position, "etaSeconds": item.eta_seconds},
                user_id=item.user_id,
            )
