from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Session, SessionStatus


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, session_id: str) -> Session | None:
        return await self.db.get(Session, session_id)

    async def create(self, session: Session) -> Session:
        self.db.add(session)
        await self.db.flush()
        return session

    async def list_active(self) -> list[Session]:
        result = await self.db.execute(
            select(Session)
            .where(Session.status.in_([SessionStatus.starting, SessionStatus.running, SessionStatus.idle, SessionStatus.terminating]))
            .options(selectinload(Session.user), selectinload(Session.profile), selectinload(Session.node))
            .order_by(Session.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_user(self, user_id: str) -> list[Session]:
        result = await self.db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .options(selectinload(Session.user), selectinload(Session.profile), selectinload(Session.node))
            .order_by(Session.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_user_active_sessions(self, user_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Session.id)).where(
                Session.user_id == user_id,
                Session.status.in_([SessionStatus.starting, SessionStatus.running, SessionStatus.idle]),
            )
        )
        return int(result.scalar_one())
