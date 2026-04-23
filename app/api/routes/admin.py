from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_dashboard_service, get_queue_service, get_session_service, require_admin
from app.db.session import get_db
from app.models import AuditLog, User
from app.schemas.dashboard import AdminDashboardResponse
from app.schemas.queue import QueueAdminActionResponse
from app.schemas.session import SessionActionResponse
from app.services.dashboard_service import DashboardService
from app.services.queue_service import QueueService
from app.services.session_service import SessionService

router = APIRouter(tags=["admin"])


class WarnPayload(BaseModel):
    message: Annotated[str, StringConstraints(min_length=5, max_length=500)] = (
        "Проверьте загрузку и сохраните прогресс"
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty")
        return cleaned


class LimitPayload(BaseModel):
    maxActiveSessions: int = Field(ge=1, le=16)
    maxQueuedRequests: int = Field(ge=1, le=64)


@router.get("/dashboard/admin", response_model=AdminDashboardResponse)
async def get_admin_dashboard(
    _: User = Depends(require_admin),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> AdminDashboardResponse:
    payload = await dashboard_service.get_admin_dashboard()
    return AdminDashboardResponse(**payload)


@router.post("/admin/queue/{queue_id}/promote", response_model=QueueAdminActionResponse)
async def promote_queue_item(
    queue_id: str,
    admin: User = Depends(require_admin),
    queue_service: QueueService = Depends(get_queue_service),
) -> QueueAdminActionResponse:
    item = await queue_service.promote(admin, queue_id)
    return QueueAdminActionResponse(queueId=item.id, status=item.status, message="Queue item promoted")


@router.delete("/admin/queue/{queue_id}", response_model=QueueAdminActionResponse)
async def delete_queue_item(
    queue_id: str,
    admin: User = Depends(require_admin),
    queue_service: QueueService = Depends(get_queue_service),
) -> QueueAdminActionResponse:
    item = await queue_service.delete(admin, queue_id)
    return QueueAdminActionResponse(queueId=item.id, status=item.status, message="Queue item removed")


@router.post("/admin/sessions/{session_id}/terminate", response_model=SessionActionResponse)
async def terminate_session(
    session_id: str,
    admin: User = Depends(require_admin),
    session_service: SessionService = Depends(get_session_service),
) -> SessionActionResponse:
    session = await session_service.terminate(admin, session_id, is_admin=True, reason="terminated_by_admin")
    return SessionActionResponse(sessionId=session.id, status=session.status, message="Session termination started")


@router.post("/admin/sessions/{session_id}/warn", response_model=SessionActionResponse)
async def warn_session(
    session_id: str,
    payload: WarnPayload,
    admin: User = Depends(require_admin),
    session_service: SessionService = Depends(get_session_service),
) -> SessionActionResponse:
    session = await session_service.warn(admin, session_id, payload.message)
    return SessionActionResponse(sessionId=session.id, status=session.status, message="Warning sent")


@router.post("/admin/users/{user_id}/block")
async def block_user(
    user_id: str,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found", "details": {}}},
        )
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "ADMIN_SELF_BLOCK_FORBIDDEN", "message": "Admin cannot block self", "details": {}}},
        )
    if user.role.value == "admin":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "ADMIN_BLOCK_FORBIDDEN",
                    "message": "Blocking admin accounts is forbidden via API",
                    "details": {},
                }
            },
        )

    user.is_blocked = True
    db.add(AuditLog(actor_user_id=admin.id, action="user.block", entity_type="user", entity_id=user.id, meta={}))
    await db.commit()
    await request.app.state.realtime_manager.disconnect_user(user.id, code=1008, reason="user_blocked")
    return {"userId": user.id, "blocked": True}


@router.post("/admin/users/{user_id}/unblock")
async def unblock_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found", "details": {}}},
        )

    user.is_blocked = False
    db.add(AuditLog(actor_user_id=admin.id, action="user.unblock", entity_type="user", entity_id=user.id, meta={}))
    await db.commit()
    return {"userId": user.id, "blocked": False}


@router.patch("/admin/users/{user_id}/limits")
async def update_limits(
    user_id: str,
    payload: LimitPayload,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found", "details": {}}},
        )

    user.max_active_sessions = payload.maxActiveSessions
    user.max_queued_requests = payload.maxQueuedRequests
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="user.update_limits",
            entity_type="user",
            entity_id=user.id,
            meta={"max_active_sessions": payload.maxActiveSessions, "max_queued_requests": payload.maxQueuedRequests},
        )
    )
    await db.commit()
    return {
        "userId": user.id,
        "maxActiveSessions": user.max_active_sessions,
        "maxQueuedRequests": user.max_queued_requests,
    }
