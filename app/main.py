from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import admin_router, auth_router, user_router
from app.config import get_settings
from app.core.auth_guard import LoginGuard
from app.core.realtime import RealtimeManager
from app.core.runtime_guard import validate_runtime_safety
from app.core.security import decode_access_token
from app.core.ws_origin import is_allowed_ws_origin
from app.db.base import Base
from app.db.bootstrap_migrations import apply_bootstrap_schema_patches
from app.db.session import AsyncSessionLocal, engine
from app.integrations.jupyterhub.mock import MockJupyterHubAdapter
from app.integrations.metrics.mock import MockMetricsAdapter
from app.integrations.slurm.mock import MockSlurmAdapter
from app.seed.seed_data import seed_data
from app.services.scheduler_service import SchedulerService
from app.services.session_service import SessionService
from app.workers.queue_worker import run_queue_worker
from app.workers.session_worker import run_session_worker
from app.models import User

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app import models as _models  # noqa: F401
    validate_runtime_safety(settings)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await apply_bootstrap_schema_patches(engine)

    app.state.realtime_manager = RealtimeManager()
    app.state.login_guard = LoginGuard(
        settings.login_max_attempts,
        settings.login_lockout_seconds,
        state_ttl_seconds=settings.login_guard_state_ttl_seconds,
        max_states=settings.login_guard_max_states,
    )
    app.state.slurm_adapter = MockSlurmAdapter()
    app.state.jupyterhub_adapter = MockJupyterHubAdapter()
    app.state.metrics_adapter = MockMetricsAdapter()

    if settings.seed_on_startup:
        async with AsyncSessionLocal() as db:
            await seed_data(db, settings)

    stop_event = asyncio.Event()
    app.state.stop_event = stop_event

    def scheduler_factory(db):
        return SchedulerService(
            db,
            settings,
            app.state.realtime_manager,
            app.state.slurm_adapter,
            app.state.jupyterhub_adapter,
        )

    def session_factory(db):
        return SessionService(
            db,
            settings,
            app.state.realtime_manager,
            app.state.slurm_adapter,
            app.state.jupyterhub_adapter,
            app.state.metrics_adapter,
        )

    app.state.queue_worker_task = asyncio.create_task(
        run_queue_worker(scheduler_factory, settings.queue_tick_seconds, stop_event)
    )
    app.state.session_worker_task = asyncio.create_task(
        run_session_worker(session_factory, settings.session_tick_seconds, stop_event)
    )

    yield

    stop_event.set()
    await asyncio.gather(app.state.queue_worker_task, app.state.session_worker_task, return_exceptions=True)
    await engine.dispose()


app = FastAPI(title="GPUFlow Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(user_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)


def _normalize_error_payload(
    detail: object,
    status_code: int,
    default_code: str,
    default_message: str,
    default_details: dict | None = None,
) -> dict:
    if isinstance(detail, dict):
        if isinstance(detail.get("error"), dict):
            err = detail["error"]
            return {
                "error": {
                    "code": err.get("code", default_code),
                    "message": err.get("message", default_message),
                    "details": err.get("details", default_details or {}),
                }
            }
        return {
            "error": {
                "code": detail.get("code", default_code),
                "message": detail.get("message", default_message),
                "details": detail.get("details", default_details or {}),
            }
        }

    if isinstance(detail, str):
        return {"error": {"code": default_code, "message": detail, "details": default_details or {}}}

    return {"error": {"code": default_code, "message": default_message, "details": default_details or {}}}


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException) -> JSONResponse:
    payload = _normalize_error_payload(
        detail=exc.detail,
        status_code=exc.status_code,
        default_code=f"HTTP_{exc.status_code}",
        default_message="Request failed",
    )
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError) -> JSONResponse:
    payload = _normalize_error_payload(
        detail={},
        status_code=422,
        default_code="VALIDATION_ERROR",
        default_message="Request validation failed",
        default_details={"fields": exc.errors()},
    )
    return JSONResponse(status_code=422, content=payload)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, __: Exception) -> JSONResponse:
    payload = _normalize_error_payload(
        detail={},
        status_code=500,
        default_code="INTERNAL_SERVER_ERROR",
        default_message="Internal server error",
    )
    return JSONResponse(status_code=500, content=payload)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


def _extract_ws_token(websocket: WebSocket) -> str | None:
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()

    subprotocols = websocket.scope.get("subprotocols") or []
    for protocol in subprotocols:
        if protocol.startswith("bearer."):
            token = protocol.split("bearer.", 1)[1].strip()
            if token:
                return token
    return None


def _select_ws_subprotocol(websocket: WebSocket) -> str | None:
    subprotocols = websocket.scope.get("subprotocols") or []
    if "gpuflow.v1" in subprotocols:
        return "gpuflow.v1"
    return None


async def _is_user_blocked(user_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
    return (not user) or bool(user.is_blocked)


@app.websocket(f"{settings.api_v1_prefix}/stream")
async def stream(websocket: WebSocket) -> None:
    origin = websocket.headers.get("origin")
    if not is_allowed_ws_origin(origin, settings.cors_allow_origins):
        await websocket.close(code=1008)
        return

    token = _extract_ws_token(websocket)

    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = decode_access_token(token)
    except Exception:  # noqa: BLE001
        await websocket.close(code=1008)
        return

    user_id = str(payload.get("sub", ""))
    if not user_id:
        await websocket.close(code=1008)
        return

    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
    if not user or user.is_blocked:
        await websocket.close(code=1008)
        return

    role = user.role.value
    manager: RealtimeManager = websocket.app.state.realtime_manager

    await manager.connect(websocket, role=role, user_id=user_id, subprotocol=_select_ws_subprotocol(websocket))
    last_auth_check = time.monotonic()
    try:
        while True:
            try:
                raw_message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.ws_heartbeat_timeout_seconds,
                )
            except TimeoutError:
                await websocket.close(code=1001)
                break
            except WebSocketDisconnect:
                break

            if raw_message:
                try:
                    decoded = json.loads(raw_message)
                except json.JSONDecodeError:
                    decoded = None

                if raw_message == "ping" or (isinstance(decoded, dict) and decoded.get("type") == "ping"):
                    if await _is_user_blocked(user_id):
                        await websocket.close(code=1008)
                        break
                    await websocket.send_json({"type": "pong"})

            now_ts = time.monotonic()
            if now_ts - last_auth_check >= settings.ws_auth_recheck_seconds:
                if await _is_user_blocked(user_id):
                    await websocket.close(code=1008)
                    break
                last_auth_check = now_ts
    finally:
        await manager.disconnect(websocket)
