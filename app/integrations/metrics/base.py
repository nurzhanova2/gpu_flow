from __future__ import annotations

from abc import ABC, abstractmethod


class MetricsAdapter(ABC):
    @abstractmethod
    async def get_nodes(self, node_count: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    async def get_usage(self, total_gpu: int, used_gpu: int, queue_depth: int) -> dict:
        raise NotImplementedError
