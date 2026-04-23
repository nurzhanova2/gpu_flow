from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(slots=True)
class LoginAttemptState:
    failures: int
    lock_until: datetime | None
    updated_at: datetime


class LoginGuard:
    def __init__(
        self,
        max_attempts: int,
        lockout_seconds: int,
        state_ttl_seconds: int = 3600,
        max_states: int = 10000,
    ) -> None:
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self.state_ttl_seconds = state_ttl_seconds
        self.max_states = max_states
        self._states: OrderedDict[str, LoginAttemptState] = OrderedDict()
        self._lock = asyncio.Lock()

    def _cleanup_expired(self, now: datetime) -> None:
        if not self._states:
            return

        ttl = timedelta(seconds=self.state_ttl_seconds)
        for key, state in list(self._states.items()):
            if state.lock_until and state.lock_until > now:
                continue
            if now - state.updated_at >= ttl:
                self._states.pop(key, None)

    def _enforce_capacity(self) -> None:
        while len(self._states) > self.max_states:
            self._states.popitem(last=False)

    async def assert_not_locked(self, key: str) -> None:
        async with self._lock:
            now = datetime.now(UTC)
            self._cleanup_expired(now)
            state = self._states.get(key)
            if not state:
                return

            if state.lock_until and state.lock_until > now:
                state.updated_at = now
                self._states.move_to_end(key)
                raise PermissionError("AUTH_LOGIN_TEMPORARILY_BLOCKED")

            if state.lock_until and state.lock_until <= now:
                self._states.pop(key, None)

    async def register_failure(self, key: str) -> None:
        async with self._lock:
            now = datetime.now(UTC)
            self._cleanup_expired(now)
            state = self._states.get(key)
            if not state:
                state = LoginAttemptState(failures=0, lock_until=None, updated_at=now)

            state.failures += 1
            if state.failures >= self.max_attempts:
                state.lock_until = now + timedelta(seconds=self.lockout_seconds)
            state.updated_at = now
            self._states[key] = state
            self._states.move_to_end(key)
            self._enforce_capacity()

    async def register_success(self, key: str) -> None:
        async with self._lock:
            self._cleanup_expired(datetime.now(UTC))
            self._states.pop(key, None)
