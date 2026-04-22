from __future__ import annotations

from abc import ABC, abstractmethod


class JupyterHubAdapter(ABC):
    @abstractmethod
    async def start_server(self, user_id: str, session_id: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def stop_server(self, jupyter_server_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_url(self, jupyter_server_id: str) -> str | None:
        raise NotImplementedError
