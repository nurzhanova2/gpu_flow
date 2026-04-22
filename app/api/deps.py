from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User, UserRole
from app.services.dashboard_service import DashboardService
from app.services.queue_service import QueueService
from app.services.scheduler_service import SchedulerService
from app.services.session_service import SessionService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_app_settings() -> Settings:
    return get_settings()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    payload = decode_access_token(token)
    user = await db.get(User, payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "AUTH_USER_NOT_FOUND", "message": "User not found", "details": {}}},
        )
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "AUTH_USER_BLOCKED", "message": "User is blocked", "details": {}}},
        )
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Admin access required", "details": {}}},
        )
    return user


def get_queue_service(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> QueueService:
    return QueueService(db, settings, request.app.state.realtime_manager, request.app.state.slurm_adapter)


def get_session_service(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> SessionService:
    return SessionService(
        db,
        settings,
        request.app.state.realtime_manager,
        request.app.state.slurm_adapter,
        request.app.state.jupyterhub_adapter,
        request.app.state.metrics_adapter,
    )


def get_dashboard_service(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> DashboardService:
    return DashboardService(db, settings, request.app.state.metrics_adapter)


def get_scheduler_service(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> SchedulerService:
    return SchedulerService(
        db,
        settings,
        request.app.state.realtime_manager,
        request.app.state.slurm_adapter,
        request.app.state.jupyterhub_adapter,
    )
