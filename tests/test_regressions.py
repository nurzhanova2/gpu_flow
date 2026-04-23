import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.config import Settings
from app.core.auth_guard import LoginGuard
from app.core.db_lock import release_worker_lock, try_acquire_worker_lock
from app.core.runtime_guard import validate_runtime_safety
from app.core.ws_origin import is_allowed_ws_origin
from app.main import app, health, lifespan
from app.models.alert import AuditLog
from app.schemas.user import RegisterRequest


class ConfigRegressionTests(unittest.TestCase):
    def test_cors_allow_origins_csv_parsed(self) -> None:
        with patch.dict(os.environ, {"CORS_ALLOW_ORIGINS": "http://localhost:5173,http://127.0.0.1:5173"}, clear=False):
            settings = Settings(_env_file=None)
        self.assertEqual(settings.cors_allow_origins, ["http://localhost:5173", "http://127.0.0.1:5173"])

    def test_cors_allow_origins_json_array_parsed(self) -> None:
        with patch.dict(os.environ, {"CORS_ALLOW_ORIGINS": '["http://a.local","http://b.local"]'}, clear=False):
            settings = Settings(_env_file=None)
        self.assertEqual(settings.cors_allow_origins, ["http://a.local", "http://b.local"])


class AuthSchemaRegressionTests(unittest.TestCase):
    def test_register_schema_accepts_local_email_for_dev(self) -> None:
        payload = RegisterRequest(
            username="user_1",
            full_name="User One",
            email="user_1@gpuflow.local",
            team="ML",
            password="password123",
        )
        self.assertEqual(payload.email, "user_1@gpuflow.local")

    def test_register_schema_rejects_invalid_email(self) -> None:
        with self.assertRaises(Exception):
            RegisterRequest(
                username="user_2",
                full_name="User Two",
                email="invalid-email",
                team="ML",
                password="password123",
            )

    def test_register_schema_rejects_weak_password(self) -> None:
        with self.assertRaises(Exception):
            RegisterRequest(
                username="user_3",
                full_name="User Three",
                email="user_3@gpuflow.local",
                team="ML",
                password="abcdefgh",
            )

        with self.assertRaises(Exception):
            RegisterRequest(
                username="user_4",
                full_name="User Four",
                email="user_4@gpuflow.local",
                team="ML",
                password="12345678",
            )


class AuthGuardRegressionTests(unittest.TestCase):
    def test_login_guard_eviction_under_unique_usernames(self) -> None:
        async def run() -> None:
            guard = LoginGuard(
                max_attempts=5,
                lockout_seconds=300,
                state_ttl_seconds=1,
                max_states=3,
            )

            for idx in range(4):
                await guard.register_failure(f"uniq_user_{idx}:127.0.0.1")

            self.assertEqual(len(guard._states), 3)
            self.assertNotIn("uniq_user_0:127.0.0.1", guard._states)

            await asyncio.sleep(1.1)
            await guard.assert_not_locked("trigger_cleanup:127.0.0.1")
            self.assertEqual(len(guard._states), 0)

        asyncio.run(run())


class WsOriginRegressionTests(unittest.TestCase):
    def test_ws_origin_allowlist(self) -> None:
        allowed = ["http://localhost:5173", "https://ui.example.com"]
        self.assertTrue(is_allowed_ws_origin("http://localhost:5173", allowed))
        self.assertTrue(is_allowed_ws_origin("https://ui.example.com", allowed))
        self.assertTrue(is_allowed_ws_origin(None, allowed))
        self.assertFalse(is_allowed_ws_origin("https://evil.example.com", allowed))


class RuntimeGuardRegressionTests(unittest.TestCase):
    def test_prod_guard_blocks_insecure_config(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "prod",
                "JWT_SECRET": "dev-secret",
                "SLURM_MODE": "mock",
                "JUPYTERHUB_MODE": "mock",
                "METRICS_MODE": "mock",
                "SEED_ON_STARTUP": "true",
                "ALLOW_USER_REGISTRATION": "true",
            },
            clear=False,
        ):
            settings = Settings(_env_file=None)
            with self.assertRaises(RuntimeError):
                validate_runtime_safety(settings)

    def test_prod_guard_accepts_safe_config(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "prod",
                "JWT_SECRET": "super-secure-production-secret-1234567890",
                "SLURM_MODE": "real",
                "JUPYTERHUB_MODE": "real",
                "METRICS_MODE": "real",
                "SEED_ON_STARTUP": "false",
                "ALLOW_USER_REGISTRATION": "false",
                "CORS_ALLOW_ORIGINS": "https://ui.example.com",
            },
            clear=False,
        ):
            settings = Settings(_env_file=None)
            validate_runtime_safety(settings)


class ModelRegressionTests(unittest.TestCase):
    def test_auditlog_uses_meta_attribute_and_metadata_column(self) -> None:
        mapper_attrs = set(AuditLog.__mapper__.attrs.keys())
        table_columns = set(AuditLog.__table__.columns.keys())

        self.assertIn("meta", mapper_attrs)
        self.assertNotIn("metadata", mapper_attrs)
        self.assertIn("metadata", table_columns)

        log = AuditLog(action="x", entity_type="y", meta={"ok": True})
        self.assertEqual(log.meta, {"ok": True})


class StartupRegressionTests(unittest.TestCase):
    def test_app_lifespan_startup_shutdown(self) -> None:
        async def run_lifespan() -> None:
            ctx = lifespan(app)
            await ctx.__aenter__()
            self.assertTrue(hasattr(app.state, "realtime_manager"))
            self.assertTrue(hasattr(app.state, "login_guard"))
            self.assertEqual(await health(), {"status": "ok"})
            await ctx.__aexit__(None, None, None)

        asyncio.run(run_lifespan())


class DbLockRegressionTests(unittest.TestCase):
    def test_try_acquire_uses_transaction_level_advisory_lock(self) -> None:
        class DummyResult:
            @staticmethod
            def scalar() -> bool:
                return True

        class DummySession:
            def __init__(self) -> None:
                self.last_query = ""

            @staticmethod
            def get_bind():
                return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

            async def execute(self, query, params=None):
                self.last_query = str(query)
                return DummyResult()

        async def run() -> None:
            session = DummySession()
            ok = await try_acquire_worker_lock(session, "gpuflow.queue_worker", True)
            self.assertTrue(ok)
            self.assertIn("pg_try_advisory_xact_lock", session.last_query)

        asyncio.run(run())

    def test_release_worker_lock_is_noop(self) -> None:
        class DummySession:
            @staticmethod
            def get_bind():
                return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

            async def execute(self, query, params=None):
                raise AssertionError("release_worker_lock must not call execute for xact lock")

        async def run() -> None:
            session = DummySession()
            await release_worker_lock(session, "gpuflow.queue_worker", True)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
