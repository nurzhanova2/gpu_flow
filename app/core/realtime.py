from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket


@dataclass(slots=True)
class ClientConnection:
    websocket: WebSocket
    role: str
    user_id: str


class RealtimeManager:
    def __init__(self) -> None:
        self._clients: list[ClientConnection] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, role: str, user_id: str, subprotocol: str | None = None) -> None:
        await websocket.accept(subprotocol=subprotocol)
        client = ClientConnection(websocket=websocket, role=role, user_id=user_id)
        async with self._lock:
            self._clients.append(client)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients = [client for client in self._clients if client.websocket is not websocket]

    async def disconnect_user(self, user_id: str, code: int = 1008, reason: str | None = None) -> int:
        async with self._lock:
            targets = [client.websocket for client in self._clients if client.user_id == user_id]

        for websocket in targets:
            try:
                await websocket.close(code=code, reason=reason)
            except Exception:  # noqa: BLE001
                pass
            await self.disconnect(websocket)
        return len(targets)

    async def publish(
        self,
        event: str,
        payload: dict[str, Any],
        roles: set[str] | None = None,
        user_id: str | None = None,
    ) -> None:
        message = {
            "event": event,
            "updatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "payload": payload,
        }

        async with self._lock:
            clients = list(self._clients)

        for client in clients:
            if roles and client.role not in roles:
                continue
            if user_id and client.user_id != user_id:
                continue
            try:
                await client.websocket.send_json(message)
            except Exception:  # noqa: BLE001
                await self.disconnect(client.websocket)

    async def publish_admin(self, event: str, payload: dict[str, Any]) -> None:
        await self.publish(event, payload, roles={"admin"})

    async def publish_user(self, event: str, payload: dict[str, Any], user_id: str) -> None:
        await self.publish(event, payload, roles={"user"}, user_id=user_id)

    async def publish_admin_and_user(self, event: str, payload: dict[str, Any], user_id: str) -> None:
        await self.publish_admin(event, payload)
        await self.publish_user(event, payload, user_id=user_id)
