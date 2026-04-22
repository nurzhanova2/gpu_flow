from __future__ import annotations

import asyncio
import json
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from uuid import uuid4


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
