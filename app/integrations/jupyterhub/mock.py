from __future__ import annotations

from uuid import uuid4

from app.integrations.jupyterhub.base import JupyterHubAdapter


class MockJupyterHubAdapter(JupyterHubAdapter):
    def __init__(self) -> None:
        self.servers: dict[str, dict] = {}

    async def start_server(self, user_id: str, session_id: str) -> dict:
        server_id = f"jhub_{uuid4().hex[:10]}"
        url = f"https://mock-jupyter.local/user/{user_id}/lab?session={session_id}"
        self.servers[server_id] = {"url": url, "active": True}
        return {"server_id": server_id, "url": url}

    async def stop_server(self, jupyter_server_id: str) -> bool:
        server = self.servers.get(jupyter_server_id)
        if not server:
            return False
        server["active"] = False
        return True

    async def get_url(self, jupyter_server_id: str) -> str | None:
        server = self.servers.get(jupyter_server_id)
        if not server:
            return None
        return server["url"]
