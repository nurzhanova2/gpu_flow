from __future__ import annotations

from random import randint

from app.integrations.metrics.base import MetricsAdapter


class MockMetricsAdapter(MetricsAdapter):
    async def get_nodes(self, node_count: int) -> list[dict]:
        return [
            {
                "cpu": randint(8, 92),
                "ram": randint(16, 88),
                "temperature": randint(34, 78),
                "uptimeIncrement": randint(0, 2),
            }
            for _ in range(node_count)
        ]

    async def get_usage(self, total_gpu: int, used_gpu: int, queue_depth: int) -> dict:
        utilization = 0
        if total_gpu > 0:
            utilization = round((used_gpu / total_gpu) * 100)
        return {
            "gpuUtilization": utilization,
            "queueDepth": queue_depth,
            "idleGpu": max(total_gpu - used_gpu, 0),
        }
