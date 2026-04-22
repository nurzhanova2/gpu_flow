from __future__ import annotations

from datetime import UTC, datetime
from random import random
from uuid import uuid4

from app.integrations.slurm.base import SlurmAdapter


class MockSlurmAdapter(SlurmAdapter):
    def __init__(self) -> None:
        self.jobs: dict[str, dict] = {}

    async def submit_job(self, queue_id: str, profile_id: str, user_id: str) -> dict:
        job_id = f"slurm_{uuid4().hex[:10]}"
        self.jobs[job_id] = {
            "queue_id": queue_id,
            "profile_id": profile_id,
            "user_id": user_id,
            "status": "PENDING",
            "created_at": datetime.now(UTC),
        }
        return {"job_id": job_id, "status": "PENDING"}

    async def cancel_job(self, slurm_job_id: str) -> bool:
        if slurm_job_id in self.jobs:
            self.jobs[slurm_job_id]["status"] = "CANCELLED"
            return True
        return False

    async def get_status(self, slurm_job_id: str) -> str:
        job = self.jobs.get(slurm_job_id)
        if not job:
            return "UNKNOWN"

        if job["status"] in {"CANCELLED", "FAILED", "COMPLETED"}:
            return job["status"]

        if random() < 0.05:
            job["status"] = "FAILED"
        elif random() < 0.35:
            job["status"] = "RUNNING"

        return job["status"]
