from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: str) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_username_for_update(self, username: str) -> User | None:
        query = select(User).where(User.username == username)
        bind = self.db.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_regular_users(self) -> list[User]:
        result = await self.db.execute(select(User).where(User.role == UserRole.user))
        return list(result.scalars().all())

    async def list_all(self) -> list[User]:
        result = await self.db.execute(select(User))
        return list(result.scalars().all())
