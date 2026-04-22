from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine


async def apply_bootstrap_schema_patches(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        table_names = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        if "users" not in table_names:
            return

        existing_columns = await conn.run_sync(
            lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("users")}
        )

        dialect = conn.dialect.name

        if "failed_login_attempts" not in existing_columns:
            await conn.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0"
                )
            )

        if "login_locked_until" not in existing_columns:
            if dialect == "postgresql":
                column_type = "TIMESTAMP WITH TIME ZONE"
            else:
                column_type = "DATETIME"

            await conn.execute(
                text(
                    "ALTER TABLE users "
                    f"ADD COLUMN login_locked_until {column_type} NULL"
                )
            )
