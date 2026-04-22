from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import QueueItem, QueueStatus


class QueueRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, queue_id: str) -> QueueItem | None:
        return await self.db.get(QueueItem, queue_id)

    async def create(self, item: QueueItem) -> QueueItem:
        self.db.add(item)
        await self.db.flush()
        return item

    async def list_active(self) -> list[QueueItem]:
        result = await self.db.execute(
            select(QueueItem)
            .where(QueueItem.is_archived.is_(False), QueueItem.status.in_([QueueStatus.waiting, QueueStatus.starting, QueueStatus.running]))
            .options(selectinload(QueueItem.user), selectinload(QueueItem.profile))
            .order_by(QueueItem.priority.desc(), QueueItem.requested_at.asc())
        )
        return list(result.scalars().all())

    async def list_waiting(self) -> list[QueueItem]:
        result = await self.db.execute(
            select(QueueItem)
            .where(QueueItem.status == QueueStatus.waiting, QueueItem.is_archived.is_(False))
            .options(selectinload(QueueItem.user), selectinload(QueueItem.profile))
            .order_by(QueueItem.priority.desc(), QueueItem.requested_at.asc())
        )
        return list(result.scalars().all())

    async def count_user_active_queue(self, user_id: str) -> int:
        result = await self.db.execute(
            select(func.count(QueueItem.id)).where(
                QueueItem.user_id == user_id,
                QueueItem.is_archived.is_(False),
                QueueItem.status.in_([QueueStatus.waiting, QueueStatus.starting]),
            )
        )
        return int(result.scalar_one())
