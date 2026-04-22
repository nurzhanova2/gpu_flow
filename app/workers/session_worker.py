from __future__ import annotations

import asyncio
import logging

from app.core.db_lock import release_worker_lock, try_acquire_worker_lock
from app.db.session import AsyncSessionLocal
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)


async def run_session_worker(service_factory, tick_seconds: int, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                service: SessionService = service_factory(db)
                if not service.settings.workers_enabled:
                    continue

                lock_name = "gpuflow.session_worker"
                acquired = await try_acquire_worker_lock(db, lock_name, service.settings.workers_use_db_lock)
                if not acquired:
                    continue

                try:
                    await service.process_session_tick()
                finally:
                    await release_worker_lock(db, lock_name, service.settings.workers_use_db_lock)
        except Exception:  # noqa: BLE001
            logger.exception("Session worker tick failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=tick_seconds)
        except TimeoutError:
            continue
