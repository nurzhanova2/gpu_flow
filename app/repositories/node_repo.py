from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Node, NodeStatus


class NodeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_nodes(self) -> list[Node]:
        result = await self.db.execute(select(Node).order_by(Node.hostname.asc()))
        return list(result.scalars().all())

    async def get_available_node(self, gpu_required: int) -> Node | None:
        if gpu_required == 0:
            result = await self.db.execute(
                select(Node).where(Node.status.in_([NodeStatus.healthy, NodeStatus.standby])).order_by(Node.gpu_used.asc(), Node.hostname.asc())
            )
            return result.scalars().first()

        result = await self.db.execute(
            select(Node)
            .where(Node.status.in_([NodeStatus.healthy, NodeStatus.standby]), Node.gpu_total - Node.gpu_used >= gpu_required)
            .order_by((Node.gpu_total - Node.gpu_used).desc(), Node.hostname.asc())
        )
        return result.scalars().first()
