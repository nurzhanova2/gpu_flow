from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SlurmAdapter(ABC):
    @abstractmethod
    async def submit_job(self, queue_id: str, profile_id: str, user_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def cancel_job(self, slurm_job_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_status(self, slurm_job_id: str) -> str:
        raise NotImplementedError
