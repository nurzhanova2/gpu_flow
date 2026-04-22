from __future__ import annotations

import zlib

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _to_lock_key(name: str) -> int:
    value = zlib.crc32(name.encode("utf-8"))
    if value > 2_147_483_647:
        value -= 4_294_967_296
    return value


async def try_acquire_worker_lock(db: AsyncSession, lock_name: str, use_db_lock: bool) -> bool:
    if not use_db_lock:
        return True

    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return True

    key = _to_lock_key(lock_name)
    # Use transaction-level advisory lock to avoid connection affinity issues.
    # Lock is auto-released on commit/rollback.
    result = await db.execute(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": key})
    return bool(result.scalar())


async def release_worker_lock(db: AsyncSession, lock_name: str, use_db_lock: bool) -> None:
    # For transaction-level locks explicit unlock is unnecessary.
    # Keep the function to preserve call sites.
    _ = (db, lock_name, use_db_lock)
    return
