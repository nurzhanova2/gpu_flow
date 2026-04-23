from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app.config import get_settings
from app.core.realtime import RealtimeManager
from app.db.session import AsyncSessionLocal, engine
from app.integrations.jupyterhub.mock import MockJupyterHubAdapter
from app.integrations.metrics.mock import MockMetricsAdapter
from app.integrations.slurm.mock import MockSlurmAdapter
from app.models import Node, NodeStatus, QueueItem, QueueStatus, Session, SessionStatus
from app.services.scheduler_service import SchedulerService
from app.services.session_service import SessionService


def _call_json(
    base_url: str,
    method: str,
    path: str,
    token: str | None = None,
    body: dict | None = None,
) -> tuple[int, dict]:
    url = f"{base_url}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, (json.loads(raw) if raw else {})


def _to_ws_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme == "https":
        ws_scheme = "wss"
    else:
        ws_scheme = "ws"
    return f"{ws_scheme}://{parsed.netloc}/api/v1/stream"


class ProdReadinessLiveTests(unittest.TestCase):
    base_url = "http://127.0.0.1:8000"

    @classmethod
    def setUpClass(cls) -> None:
        cls._db_loop = asyncio.new_event_loop()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._db_loop.run_until_complete(engine.dispose())
        cls._db_loop.close()

    def _run_db(self, coro):
        return self._db_loop.run_until_complete(coro)

    def _login_admin(self) -> str:
        status, payload = _call_json(
            self.base_url,
            "POST",
            "/api/v1/auth/login",
            body={"username": "admin", "password": "admin123"},
        )
        self.assertEqual(status, 200, payload)
        return payload["access_token"]

    def _register_user(self, prefix: str) -> tuple[str, str, str]:
        suffix = uuid4().hex[:8]
        username = f"{prefix}_{suffix}"
        password = "testpass123"
        payload = {
            "username": username,
            "full_name": f"{prefix} user {suffix}",
            "email": f"{username}@gpuflow.local",
            "team": "QA",
            "password": password,
        }
        status, body = _call_json(self.base_url, "POST", "/api/v1/auth/register", body=payload)
        self.assertEqual(status, 201, body)
        return body["access_token"], body["user"]["id"], body["user"]["full_name"]

    def _get_first_profile(self, token: str) -> str:
        status, payload = _call_json(self.base_url, "GET", "/api/v1/dashboard/user", token=token)
        self.assertEqual(status, 200, payload)
        launch_profiles = payload.get("launchProfiles", [])
        self.assertGreater(len(launch_profiles), 0, payload)
        return launch_profiles[0]["id"]

    def _wait_until(self, predicate, timeout_sec: float = 25.0, interval_sec: float = 1.0):
        started = time.time()
        while time.time() - started < timeout_sec:
            value = predicate()
            if value:
                return value
            time.sleep(interval_sec)
        return None

    def _force_starting_session(self, queue_id: str, user_id: str, profile_id: str) -> str:
        async def _run() -> str:
            now = datetime.now(UTC)
            async with AsyncSessionLocal() as db:
                queue_item = await db.get(QueueItem, queue_id)
                assert queue_item is not None
                queue_item.status = QueueStatus.starting
                queue_item.is_archived = False
                queue_item.status_updated_at = now

                existing = await db.scalar(select(Session).where(Session.queue_item_id == queue_id))
                if existing:
                    existing.status = SessionStatus.starting
                    existing.status_updated_at = now
                    existing.last_activity_at = now
                    existing.ended_at = None
                    existing.termination_reason = None
                    session_id = existing.id
                else:
                    session = Session(
                        user_id=user_id,
                        profile_id=profile_id,
                        queue_item_id=queue_id,
                        status=SessionStatus.starting,
                        status_updated_at=now,
                        started_at=now,
                        last_activity_at=now,
                    )
                    db.add(session)
                    await db.flush()
                    session_id = session.id
                await db.commit()
                return session_id

        return self._run_db(_run())

    def _create_relaunchable_session(self, user_id: str, profile_id: str) -> str:
        async def _run() -> str:
            now = datetime.now(UTC)
            async with AsyncSessionLocal() as db:
                session = Session(
                    user_id=user_id,
                    profile_id=profile_id,
                    status=SessionStatus.completed,
                    status_updated_at=now,
                    started_at=now - timedelta(minutes=10),
                    ended_at=now,
                )
                db.add(session)
                await db.flush()
                session_id = session.id
                await db.commit()
                return session_id

        return self._run_db(_run())

    def _run_session_termination_tick(self, session_id: str) -> None:
        async def _run() -> None:
            now = datetime.now(UTC)
            async with AsyncSessionLocal() as db:
                session = await db.get(Session, session_id)
                if session is None:
                    return
                session.status = SessionStatus.terminating
                session.status_updated_at = now - timedelta(seconds=15)
                await db.commit()

            async with AsyncSessionLocal() as db:
                service = SessionService(
                    db,
                    get_settings(),
                    RealtimeManager(),
                    MockSlurmAdapter(),
                    MockJupyterHubAdapter(),
                    MockMetricsAdapter(),
                )
                await service.process_session_tick()

        self._run_db(_run())

    def _create_session_with_status(
        self,
        user_id: str,
        profile_id: str,
        status: SessionStatus,
        *,
        notebook_url: str | None = None,
        jupyter_server_id: str | None = None,
        termination_reason: str | None = None,
        status_updated_at: datetime | None = None,
    ) -> str:
        async def _run() -> str:
            now = datetime.now(UTC)
            status_at = status_updated_at or now
            started_at = now - timedelta(minutes=5)
            ended_at = now if status in {SessionStatus.completed, SessionStatus.failed, SessionStatus.terminated} else None

            async with AsyncSessionLocal() as db:
                session = Session(
                    user_id=user_id,
                    profile_id=profile_id,
                    status=status,
                    status_updated_at=status_at,
                    started_at=started_at,
                    ended_at=ended_at,
                    notebook_url=notebook_url,
                    jupyter_server_id=jupyter_server_id,
                    termination_reason=termination_reason,
                    last_activity_at=started_at,
                    idle_since=now - timedelta(minutes=1) if status == SessionStatus.idle else None,
                )
                db.add(session)
                await db.flush()
                session_id = session.id
                await db.commit()
                return session_id

        return self._run_db(_run())

    def _get_session_snapshot(self, session_id: str) -> tuple[SessionStatus, datetime, str | None]:
        async def _run() -> tuple[SessionStatus, datetime, str | None]:
            async with AsyncSessionLocal() as db:
                session = await db.get(Session, session_id)
                assert session is not None
                return session.status, session.status_updated_at, session.termination_reason

        return self._run_db(_run())

    def _set_queue_item_state(self, queue_id: str, status: QueueStatus, *, is_archived: bool) -> None:
        async def _run() -> None:
            async with AsyncSessionLocal() as db:
                item = await db.get(QueueItem, queue_id)
                assert item is not None
                item.status = status
                item.is_archived = is_archived
                item.status_updated_at = datetime.now(UTC)
                await db.commit()

        self._run_db(_run())

    def _get_queue_snapshot(self, queue_id: str) -> tuple[QueueStatus, bool, int]:
        async def _run() -> tuple[QueueStatus, bool, int]:
            async with AsyncSessionLocal() as db:
                item = await db.get(QueueItem, queue_id)
                assert item is not None
                return item.status, bool(item.is_archived), int(item.priority)

        return self._run_db(_run())

    def _constrain_cluster_to_single_gpu_node(self) -> str:
        async def _run() -> str:
            async with AsyncSessionLocal() as db:
                nodes = list((await db.execute(select(Node).order_by(Node.hostname.asc()))).scalars().all())
                assert nodes, "No nodes seeded"
                primary = nodes[0]
                for node in nodes:
                    node.gpu_used = 0
                    if node.id == primary.id:
                        node.status = NodeStatus.healthy
                        node.gpu_total = 1
                    else:
                        node.status = NodeStatus.offline
                await db.commit()
                return primary.id

        return self._run_db(_run())

    def _run_parallel_scheduler_ticks(self) -> None:
        async def _run() -> None:
            async def _tick_once() -> None:
                async with AsyncSessionLocal() as db:
                    service = SchedulerService(
                        db,
                        get_settings(),
                        RealtimeManager(),
                        MockSlurmAdapter(),
                        MockJupyterHubAdapter(),
                    )
                    await service.process_queue_tick()

            await asyncio.gather(_tick_once(), _tick_once())

        self._run_db(_run())

    def _get_node_gpu_used(self, node_id: str) -> int:
        async def _run() -> int:
            async with AsyncSessionLocal() as db:
                node = await db.get(Node, node_id)
                assert node is not None
                return int(node.gpu_used)

        return self._run_db(_run())

    def _get_sessions_on_node_for_queue_items(self, node_id: str, queue_ids: list[str]) -> list[SessionStatus]:
        async def _run() -> list[SessionStatus]:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Session.status).where(
                        Session.node_id == node_id,
                        Session.queue_item_id.in_(queue_ids),
                        Session.status.in_([SessionStatus.starting, SessionStatus.running, SessionStatus.idle]),
                    )
                )
                return [row[0] for row in result.all()]

        return self._run_db(_run())

    def test_01_health(self) -> None:
        status, payload = _call_json(self.base_url, "GET", "/health")
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload.get("status"), "ok")

    def test_02_login_seed_users(self) -> None:
        status_admin, payload_admin = _call_json(
            self.base_url,
            "POST",
            "/api/v1/auth/login",
            body={"username": "admin", "password": "admin123"},
        )
        self.assertEqual(status_admin, 200, payload_admin)
        self.assertIn("access_token", payload_admin)

        status_demo, payload_demo = _call_json(
            self.base_url,
            "POST",
            "/api/v1/auth/login",
            body={"username": "demo", "password": "user12345"},
        )
        self.assertEqual(status_demo, 200, payload_demo)
        self.assertIn("access_token", payload_demo)

        status_short, payload_short = _call_json(
            self.base_url,
            "POST",
            "/api/v1/auth/login",
            body={"username": "demo", "password": "user123"},
        )
        self.assertEqual(status_short, 422, payload_short)
        self.assertEqual(payload_short.get("error", {}).get("code"), "VALIDATION_ERROR")

    def test_03_register_dashboard_launch_cancel_and_admin_controls(self) -> None:
        suffix = uuid4().hex[:8]
        username = f"prod_{suffix}"
        email = f"{username}@gpuflow.local"
        password = "testpass123"

        register_status, register_payload = _call_json(
            self.base_url,
            "POST",
            "/api/v1/auth/register",
            body={
                "username": username,
                "full_name": "Prod Test User",
                "email": email,
                "team": "QA",
                "password": password,
            },
        )
        self.assertEqual(register_status, 201, register_payload)
        user_token = register_payload["access_token"]
        user_id = register_payload["user"]["id"]

        user_dash_status, user_dash_payload = _call_json(
            self.base_url,
            "GET",
            "/api/v1/dashboard/user",
            token=user_token,
        )
        self.assertEqual(user_dash_status, 200, user_dash_payload)
        for key in [
            "summaryStats",
            "launchProfiles",
            "mySessionState",
            "queueSnapshot",
            "activeSessions",
            "history",
            "charts",
        ]:
            self.assertIn(key, user_dash_payload)

        launch_profiles = user_dash_payload.get("launchProfiles", [])
        self.assertGreater(len(launch_profiles), 0)
        profile_id = launch_profiles[0]["id"]

        launch_status, launch_payload = _call_json(
            self.base_url,
            "POST",
            "/api/v1/sessions/launch",
            token=user_token,
            body={"profileId": profile_id},
        )
        self.assertEqual(launch_status, 200, launch_payload)
        request_id = launch_payload["requestId"]

        cancel_status, cancel_payload = _call_json(
            self.base_url,
            "POST",
            f"/api/v1/queue/{request_id}/cancel",
            token=user_token,
        )
        self.assertEqual(cancel_status, 200, cancel_payload)

        admin_login_status, admin_login_payload = _call_json(
            self.base_url,
            "POST",
            "/api/v1/auth/login",
            body={"username": "admin", "password": "admin123"},
        )
        self.assertEqual(admin_login_status, 200, admin_login_payload)
        admin_token = admin_login_payload["access_token"]

        admin_dash_status, admin_dash_payload = _call_json(
            self.base_url,
            "GET",
            "/api/v1/dashboard/admin",
            token=admin_token,
        )
        self.assertEqual(admin_dash_status, 200, admin_dash_payload)
        for key in ["adminKpis", "alerts", "nodes", "queue", "sessions", "charts"]:
            self.assertIn(key, admin_dash_payload)

        block_status, block_payload = _call_json(
            self.base_url,
            "POST",
            f"/api/v1/admin/users/{user_id}/block",
            token=admin_token,
        )
        self.assertEqual(block_status, 200, block_payload)
        self.assertTrue(block_payload.get("blocked"))

        me_blocked_status, me_blocked_payload = _call_json(
            self.base_url,
            "GET",
            "/api/v1/auth/me",
            token=user_token,
        )
        self.assertEqual(me_blocked_status, 403, me_blocked_payload)
        self.assertEqual(me_blocked_payload.get("error", {}).get("code"), "AUTH_USER_BLOCKED")

        unblock_status, unblock_payload = _call_json(
            self.base_url,
            "POST",
            f"/api/v1/admin/users/{user_id}/unblock",
            token=admin_token,
        )
        self.assertEqual(unblock_status, 200, unblock_payload)
        self.assertFalse(unblock_payload.get("blocked"))

        me_unblocked_status, me_unblocked_payload = _call_json(
            self.base_url,
            "GET",
            "/api/v1/auth/me",
            token=user_token,
        )
        self.assertEqual(me_unblocked_status, 200, me_unblocked_payload)
        self.assertEqual(me_unblocked_payload.get("username"), username)

    def test_04_websocket_ping_pong(self) -> None:
        status, payload = _call_json(
            self.base_url,
            "POST",
            "/api/v1/auth/login",
            body={"username": "admin", "password": "admin123"},
        )
        self.assertEqual(status, 200, payload)
        token = payload["access_token"]

        async def ws_check() -> None:
            import websockets

            ws_url = _to_ws_url(self.base_url)
            async with websockets.connect(
                ws_url,
                subprotocols=["gpuflow.v1", f"bearer.{token}"],
                open_timeout=10,
                close_timeout=5,
            ) as socket:
                await socket.send(json.dumps({"type": "ping"}))
                message = await asyncio.wait_for(socket.recv(), timeout=5)
                payload = json.loads(message)
                self.assertEqual(payload.get("type"), "pong")

        asyncio.run(ws_check())

    def test_05_launch_parallel_respects_queue_limit(self) -> None:
        user_token, user_id, _ = self._register_user("race_launch")
        admin_token = self._login_admin()
        profile_id = self._get_first_profile(user_token)

        limit_status, limit_payload = _call_json(
            self.base_url,
            "PATCH",
            f"/api/v1/admin/users/{user_id}/limits",
            token=admin_token,
            body={"maxActiveSessions": 4, "maxQueuedRequests": 2},
        )
        self.assertEqual(limit_status, 200, limit_payload)

        def do_launch() -> tuple[int, dict]:
            return _call_json(
                self.base_url,
                "POST",
                "/api/v1/sessions/launch",
                token=user_token,
                body={"profileId": profile_id},
            )

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: do_launch(), range(6)))

        success = [payload for status, payload in results if status == 200]
        rejected = [payload for status, payload in results if status == 409]
        self.assertEqual(len(success), 2, results)
        self.assertEqual(len(rejected), 4, results)

        queue_ids = [item["requestId"] for item in success]
        self.assertEqual(len(queue_ids), len(set(queue_ids)), queue_ids)

        dash_status, dash_payload = _call_json(self.base_url, "GET", "/api/v1/dashboard/user", token=user_token)
        self.assertEqual(dash_status, 200, dash_payload)
        mine_active_queue = [row for row in dash_payload.get("queueSnapshot", []) if row.get("mine")]
        self.assertLessEqual(len(mine_active_queue), 2, mine_active_queue)

    def test_06_relaunch_parallel_respects_queue_limit(self) -> None:
        user_token, user_id, _ = self._register_user("race_relaunch")
        admin_token = self._login_admin()
        profile_id = self._get_first_profile(user_token)
        session_id = self._create_relaunchable_session(user_id, profile_id)

        limit_status, limit_payload = _call_json(
            self.base_url,
            "PATCH",
            f"/api/v1/admin/users/{user_id}/limits",
            token=admin_token,
            body={"maxActiveSessions": 6, "maxQueuedRequests": 2},
        )
        self.assertEqual(limit_status, 200, limit_payload)

        def do_relaunch() -> tuple[int, dict]:
            return _call_json(
                self.base_url,
                "POST",
                f"/api/v1/sessions/{session_id}/relaunch",
                token=user_token,
            )

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: do_relaunch(), range(6)))

        success = [payload for status, payload in results if status == 200]
        rejected = [payload for status, payload in results if status == 409]
        self.assertLessEqual(len(success), 2, results)
        self.assertGreaterEqual(len(rejected), 4, results)

        queue_ids = [item["requestId"] for item in success]
        self.assertEqual(len(queue_ids), len(set(queue_ids)), queue_ids)

    def test_07_admin_delete_starting_queue_transitions_session_to_terminating(self) -> None:
        user_token, user_id, _ = self._register_user("delete_starting")
        admin_token = self._login_admin()
        profile_id = self._get_first_profile(user_token)

        launch_status, launch_payload = _call_json(
            self.base_url,
            "POST",
            "/api/v1/sessions/launch",
            token=user_token,
            body={"profileId": profile_id},
        )
        self.assertEqual(launch_status, 200, launch_payload)
        queue_id = launch_payload["requestId"]
        session_id = self._force_starting_session(queue_id, user_id, profile_id)

        delete_status, delete_payload = _call_json(
            self.base_url,
            "DELETE",
            f"/api/v1/admin/queue/{queue_id}",
            token=admin_token,
        )
        self.assertEqual(delete_status, 200, delete_payload)

        def _is_session_terminating() -> bool:
            status, payload = _call_json(self.base_url, "GET", "/api/v1/dashboard/admin", token=admin_token)
            if status != 200:
                return False
            sessions = payload.get("sessions", [])
            row = next((item for item in sessions if item.get("id") == session_id), None)
            return bool(row and row.get("status") == "terminating")

        terminating = self._wait_until(_is_session_terminating, timeout_sec=8.0, interval_sec=1.0)
        self.assertTrue(bool(terminating), f"Session {session_id} did not transition to terminating")

    def test_08_no_orphan_sessions_after_queue_delete(self) -> None:
        user_token, user_id, _ = self._register_user("delete_no_orphan")
        admin_token = self._login_admin()
        profile_id = self._get_first_profile(user_token)

        launch_status, launch_payload = _call_json(
            self.base_url,
            "POST",
            "/api/v1/sessions/launch",
            token=user_token,
            body={"profileId": profile_id},
        )
        self.assertEqual(launch_status, 200, launch_payload)
        queue_id = launch_payload["requestId"]
        session_id = self._force_starting_session(queue_id, user_id, profile_id)

        delete_status, delete_payload = _call_json(
            self.base_url,
            "DELETE",
            f"/api/v1/admin/queue/{queue_id}",
            token=admin_token,
        )
        self.assertEqual(delete_status, 200, delete_payload)
        self._run_session_termination_tick(session_id)

        def _session_gone_from_active() -> bool:
            status, payload = _call_json(self.base_url, "GET", "/api/v1/dashboard/admin", token=admin_token)
            if status != 200:
                return False
            queue_ids = {row.get("id") for row in payload.get("queue", [])}
            if queue_id in queue_ids:
                return False
            session_ids = {row.get("id") for row in payload.get("sessions", [])}
            return session_id not in session_ids

        session_gone = self._wait_until(_session_gone_from_active, timeout_sec=35.0, interval_sec=1.0)
        self.assertTrue(bool(session_gone), f"Orphan active session still present: {session_id}")

    def test_09_terminate_finished_session_returns_409(self) -> None:
        user_token, user_id, _ = self._register_user("term_finished")
        admin_token = self._login_admin()
        profile_id = self._get_first_profile(user_token)
        session_id = self._create_session_with_status(
            user_id,
            profile_id,
            SessionStatus.terminated,
            notebook_url="https://notebook.local/user/term_finished",
        )

        status_code, payload = _call_json(
            self.base_url,
            "POST",
            f"/api/v1/admin/sessions/{session_id}/terminate",
            token=admin_token,
        )
        self.assertEqual(status_code, 409, payload)
        self.assertEqual(payload.get("error", {}).get("code"), "INVALID_STATE")

        session_status, _, _ = self._get_session_snapshot(session_id)
        self.assertEqual(session_status, SessionStatus.terminated)

    def test_10_terminate_is_idempotent_for_terminating(self) -> None:
        user_token, user_id, _ = self._register_user("term_idempotent")
        admin_token = self._login_admin()
        profile_id = self._get_first_profile(user_token)
        original_status_updated_at = datetime.now(UTC) - timedelta(minutes=3)
        session_id = self._create_session_with_status(
            user_id,
            profile_id,
            SessionStatus.terminating,
            notebook_url="https://notebook.local/user/term_idempotent",
            jupyter_server_id="jhub-still-stopping",
            termination_reason="idle_timeout",
            status_updated_at=original_status_updated_at,
        )

        status_code, payload = _call_json(
            self.base_url,
            "POST",
            f"/api/v1/admin/sessions/{session_id}/terminate",
            token=admin_token,
        )
        self.assertEqual(status_code, 200, payload)
        self.assertEqual(payload.get("status"), "terminating")

        session_status, status_updated_at_after, termination_reason_after = self._get_session_snapshot(session_id)
        self.assertEqual(session_status, SessionStatus.terminating)
        self.assertEqual(status_updated_at_after, original_status_updated_at)
        self.assertEqual(termination_reason_after, "idle_timeout")

    def test_11_access_denied_for_terminated_session(self) -> None:
        user_token, user_id, _ = self._register_user("access_terminated")
        profile_id = self._get_first_profile(user_token)
        session_id = self._create_session_with_status(
            user_id,
            profile_id,
            SessionStatus.terminated,
            notebook_url="https://notebook.local/user/access_terminated",
        )

        status_code, payload = _call_json(
            self.base_url,
            "GET",
            f"/api/v1/sessions/{session_id}/access",
            token=user_token,
        )
        self.assertEqual(status_code, 409, payload)
        self.assertEqual(payload.get("error", {}).get("code"), "INVALID_STATE")

    def test_12_access_returns_url_only_for_running_idle(self) -> None:
        user_token, user_id, _ = self._register_user("access_live_only")
        profile_id = self._get_first_profile(user_token)
        running_url = "https://notebook.local/user/access_live_only/running"
        idle_url = "https://notebook.local/user/access_live_only/idle"

        running_session_id = self._create_session_with_status(
            user_id,
            profile_id,
            SessionStatus.running,
            notebook_url=running_url,
            jupyter_server_id="jhub-running",
        )
        idle_session_id = self._create_session_with_status(
            user_id,
            profile_id,
            SessionStatus.idle,
            notebook_url=idle_url,
            jupyter_server_id="jhub-idle",
        )
        starting_session_id = self._create_session_with_status(
            user_id,
            profile_id,
            SessionStatus.starting,
            notebook_url="https://notebook.local/user/access_live_only/starting",
        )

        running_status, running_payload = _call_json(
            self.base_url,
            "GET",
            f"/api/v1/sessions/{running_session_id}/access",
            token=user_token,
        )
        self.assertEqual(running_status, 200, running_payload)
        self.assertEqual(running_payload.get("notebookUrl"), running_url)

        idle_status, idle_payload = _call_json(
            self.base_url,
            "GET",
            f"/api/v1/sessions/{idle_session_id}/access",
            token=user_token,
        )
        self.assertEqual(idle_status, 200, idle_payload)
        self.assertEqual(idle_payload.get("notebookUrl"), idle_url)

        starting_status, starting_payload = _call_json(
            self.base_url,
            "GET",
            f"/api/v1/sessions/{starting_session_id}/access",
            token=user_token,
        )
        self.assertEqual(starting_status, 409, starting_payload)
        self.assertEqual(starting_payload.get("error", {}).get("code"), "INVALID_STATE")

    def test_13_promote_only_waiting_items(self) -> None:
        user_token, user_id, _ = self._register_user("promote_waiting")
        admin_token = self._login_admin()
        profile_id = self._get_first_profile(user_token)

        launch_status, launch_payload = _call_json(
            self.base_url,
            "POST",
            "/api/v1/sessions/launch",
            token=user_token,
            body={"profileId": profile_id},
        )
        self.assertEqual(launch_status, 200, launch_payload)
        queue_id = launch_payload["requestId"]

        promote_status, promote_payload = _call_json(
            self.base_url,
            "POST",
            f"/api/v1/admin/queue/{queue_id}/promote",
            token=admin_token,
        )
        self.assertEqual(promote_status, 200, promote_payload)

        self._set_queue_item_state(queue_id, QueueStatus.starting, is_archived=False)
        pre_status, pre_archived, pre_priority = self._get_queue_snapshot(queue_id)
        self.assertEqual(pre_status, QueueStatus.starting)
        self.assertFalse(pre_archived)

        second_promote_status, second_promote_payload = _call_json(
            self.base_url,
            "POST",
            f"/api/v1/admin/queue/{queue_id}/promote",
            token=admin_token,
        )
        self.assertEqual(second_promote_status, 409, second_promote_payload)
        self.assertEqual(second_promote_payload.get("error", {}).get("code"), "QUEUE_ITEM_NOT_PROMOTABLE")

        post_status, post_archived, post_priority = self._get_queue_snapshot(queue_id)
        self.assertEqual(post_status, QueueStatus.starting)
        self.assertFalse(post_archived)
        self.assertEqual(post_priority, pre_priority)

    def test_14_promote_cancelled_returns_409(self) -> None:
        user_token, _, _ = self._register_user("promote_cancelled")
        admin_token = self._login_admin()
        profile_id = self._get_first_profile(user_token)

        launch_status, launch_payload = _call_json(
            self.base_url,
            "POST",
            "/api/v1/sessions/launch",
            token=user_token,
            body={"profileId": profile_id},
        )
        self.assertEqual(launch_status, 200, launch_payload)
        queue_id = launch_payload["requestId"]

        cancel_status, cancel_payload = _call_json(
            self.base_url,
            "POST",
            f"/api/v1/queue/{queue_id}/cancel",
            token=user_token,
        )
        self.assertEqual(cancel_status, 200, cancel_payload)

        promote_status, promote_payload = _call_json(
            self.base_url,
            "POST",
            f"/api/v1/admin/queue/{queue_id}/promote",
            token=admin_token,
        )
        self.assertEqual(promote_status, 409, promote_payload)
        self.assertEqual(promote_payload.get("error", {}).get("code"), "QUEUE_ITEM_NOT_PROMOTABLE")

        queue_status, is_archived, _ = self._get_queue_snapshot(queue_id)
        self.assertEqual(queue_status, QueueStatus.cancelled)
        self.assertTrue(is_archived)

    def test_15_ws_disconnect_immediately_on_user_block(self) -> None:
        user_token, user_id, _ = self._register_user("ws_block")
        admin_token = self._login_admin()

        async def ws_check() -> None:
            import websockets
            from websockets.exceptions import ConnectionClosed

            ws_url = _to_ws_url(self.base_url)
            async with websockets.connect(
                ws_url,
                subprotocols=["gpuflow.v1", f"bearer.{user_token}"],
                open_timeout=10,
                close_timeout=5,
            ) as socket:
                await socket.send(json.dumps({"type": "ping"}))
                message = await asyncio.wait_for(socket.recv(), timeout=5)
                payload = json.loads(message)
                self.assertEqual(payload.get("type"), "pong")

                block_status, block_payload = await asyncio.to_thread(
                    lambda: _call_json(
                        self.base_url,
                        "POST",
                        f"/api/v1/admin/users/{user_id}/block",
                        token=admin_token,
                    )
                )
                self.assertEqual(block_status, 200, block_payload)

                with self.assertRaises(ConnectionClosed):
                    await asyncio.wait_for(socket.recv(), timeout=5)

        asyncio.run(ws_check())

    def test_16_warn_finished_session_returns_409(self) -> None:
        user_token, user_id, _ = self._register_user("warn_finished")
        admin_token = self._login_admin()
        profile_id = self._get_first_profile(user_token)
        session_id = self._create_session_with_status(
            user_id,
            profile_id,
            SessionStatus.completed,
            notebook_url="https://notebook.local/user/warn_finished",
        )

        warn_status, warn_payload = _call_json(
            self.base_url,
            "POST",
            f"/api/v1/admin/sessions/{session_id}/warn",
            token=admin_token,
            body={"message": "Session is already finished, warning must fail"},
        )
        self.assertEqual(warn_status, 409, warn_payload)
        self.assertEqual(warn_payload.get("error", {}).get("code"), "INVALID_STATE")

    def test_17_warn_rate_limited(self) -> None:
        user_token, user_id, _ = self._register_user("warn_rate")
        admin_token = self._login_admin()
        profile_id = self._get_first_profile(user_token)
        session_id = self._create_session_with_status(
            user_id,
            profile_id,
            SessionStatus.running,
            notebook_url="https://notebook.local/user/warn_rate",
            jupyter_server_id="jhub-warn-rate",
        )

        limit = get_settings().admin_warn_rate_limit_count
        self.assertGreaterEqual(limit, 1)
        for idx in range(limit):
            warn_status, warn_payload = _call_json(
                self.base_url,
                "POST",
                f"/api/v1/admin/sessions/{session_id}/warn",
                token=admin_token,
                body={"message": f"Rate test warning {idx + 1}"},
            )
            self.assertEqual(warn_status, 200, warn_payload)

        limited_status, limited_payload = _call_json(
            self.base_url,
            "POST",
            f"/api/v1/admin/sessions/{session_id}/warn",
            token=admin_token,
            body={"message": "One warning too many"},
        )
        self.assertEqual(limited_status, 429, limited_payload)
        self.assertEqual(limited_payload.get("error", {}).get("code"), "WARN_RATE_LIMITED")

    def test_18_parallel_scheduler_does_not_oversubscribe_node(self) -> None:
        user_one_token, _, _ = self._register_user("sched_parallel_a")
        user_two_token, _, _ = self._register_user("sched_parallel_b")
        profile_id = self._get_first_profile(user_one_token)

        launch_one_status, launch_one_payload = _call_json(
            self.base_url,
            "POST",
            "/api/v1/sessions/launch",
            token=user_one_token,
            body={"profileId": profile_id},
        )
        self.assertEqual(launch_one_status, 200, launch_one_payload)
        queue_one_id = launch_one_payload["requestId"]

        launch_two_status, launch_two_payload = _call_json(
            self.base_url,
            "POST",
            "/api/v1/sessions/launch",
            token=user_two_token,
            body={"profileId": profile_id},
        )
        self.assertEqual(launch_two_status, 200, launch_two_payload)
        queue_two_id = launch_two_payload["requestId"]

        node_id = self._constrain_cluster_to_single_gpu_node()
        self._run_parallel_scheduler_ticks()

        gpu_used = self._get_node_gpu_used(node_id)
        self.assertLessEqual(gpu_used, 1)

        active_statuses = self._get_sessions_on_node_for_queue_items(node_id, [queue_one_id, queue_two_id])
        self.assertLessEqual(len(active_statuses), 1, active_statuses)


class FrontendNoMockDataTests(unittest.TestCase):
    def test_frontend_pages_do_not_import_mock_data(self) -> None:
        root = Path(__file__).resolve().parents[1] / "frontend" / "src"
        targets = list(root.rglob("*.js")) + list(root.rglob("*.jsx"))
        forbidden_hits: list[str] = []

        for file_path in targets:
            relative = file_path.relative_to(root).as_posix()
            if relative.startswith("data/"):
                continue
            text = file_path.read_text(encoding="utf-8")
            if "mockAdminData" in text or "mockUserData" in text or "/data/mock" in text:
                forbidden_hits.append(relative)

        self.assertEqual(forbidden_hits, [], f"Mock data references found: {forbidden_hits}")


if __name__ == "__main__":
    unittest.main()
