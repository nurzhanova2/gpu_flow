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

    def _is_postgres(self) -> bool:
        bind = self.db.get_bind()
        return bind is not None and bind.dialect.name == "postgresql"

    async def reserve_available_node(self, gpu_required: int) -> Node | None:
        if gpu_required == 0:
            query = select(Node).where(Node.status.in_([NodeStatus.healthy, NodeStatus.standby])).order_by(Node.gpu_used.asc(), Node.hostname.asc())
        else:
            query = (
                select(Node)
                .where(Node.status.in_([NodeStatus.healthy, NodeStatus.standby]), Node.gpu_total - Node.gpu_used >= gpu_required)
                .order_by((Node.gpu_total - Node.gpu_used).desc(), Node.hostname.asc())
            )

        if self._is_postgres():
            query = query.with_for_update(skip_locked=True)
        result = await self.db.execute(query)
        node = result.scalars().first()
        if not node:
            return None

        if gpu_required > 0:
            node.gpu_used = min(node.gpu_total, node.gpu_used + gpu_required)
        return node

    async def get_available_node(self, gpu_required: int) -> Node | None:
        # Backward-compatible alias.
        return await self.reserve_available_node(gpu_required)
