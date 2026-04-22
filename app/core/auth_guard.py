from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(slots=True)
class LoginAttemptState:
    failures: int
    lock_until: datetime | None


class LoginGuard:
    def __init__(self, max_attempts: int, lockout_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._states: dict[str, LoginAttemptState] = {}
        self._lock = asyncio.Lock()

    async def assert_not_locked(self, key: str) -> None:
        async with self._lock:
            now = datetime.now(UTC)
            state = self._states.get(key)
            if not state:
                return

            if state.lock_until and state.lock_until > now:
                raise PermissionError("AUTH_LOGIN_TEMPORARILY_BLOCKED")

            if state.lock_until and state.lock_until <= now:
                self._states.pop(key, None)

    async def register_failure(self, key: str) -> None:
        async with self._lock:
            now = datetime.now(UTC)
            state = self._states.get(key)
            if not state:
                state = LoginAttemptState(failures=0, lock_until=None)

            state.failures += 1
            if state.failures >= self.max_attempts:
                state.lock_until = now + timedelta(seconds=self.lockout_seconds)
            self._states[key] = state

    async def register_success(self, key: str) -> None:
        async with self._lock:
            self._states.pop(key, None)
