from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_dashboard_service, get_queue_service, get_session_service
from app.db.session import get_db
from app.models import LaunchProfile, User
from app.schemas.dashboard import UserDashboardResponse
from app.schemas.queue import QueueCancelResponse
from app.schemas.session import LaunchRequest, LaunchResponse, SessionAccessResponse
from app.services.dashboard_service import DashboardService
from app.services.queue_service import QueueService
from app.services.session_service import SessionService

router = APIRouter(tags=["user"])


@router.get("/dashboard/user", response_model=UserDashboardResponse)
async def get_user_dashboard(
    current_user: User = Depends(get_current_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> UserDashboardResponse:
    payload = await dashboard_service.get_user_dashboard(current_user.id)
    return UserDashboardResponse(**payload)


@router.post("/sessions/launch", response_model=LaunchResponse)
async def launch_session(
    data: LaunchRequest,
    current_user: User = Depends(get_current_user),
    queue_service: QueueService = Depends(get_queue_service),
    db: AsyncSession = Depends(get_db),
) -> LaunchResponse:
    profile = await db.get(LaunchProfile, data.profileId)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "LAUNCH_PROFILE_NOT_FOUND", "message": "Launch profile not found", "details": {}}},
        )

    item, position, eta_min = await queue_service.enqueue(current_user, profile.id)
    return LaunchResponse(requestId=item.id, status=item.status.value, queuePosition=position, etaMin=eta_min)


@router.post("/queue/{queue_id}/cancel", response_model=QueueCancelResponse)
async def cancel_queue_item(
    queue_id: str,
    current_user: User = Depends(get_current_user),
    queue_service: QueueService = Depends(get_queue_service),
) -> QueueCancelResponse:
    item = await queue_service.cancel(current_user, queue_id, is_admin=False)
    return QueueCancelResponse(queueId=item.id, status=item.status, message="Queue request cancelled")


@router.post("/sessions/{session_id}/relaunch", response_model=LaunchResponse)
async def relaunch_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> LaunchResponse:
    request_id, status_value, position, eta_min = await session_service.relaunch(current_user, session_id)
    return LaunchResponse(requestId=request_id, status=status_value, queuePosition=position, etaMin=eta_min)


@router.get("/sessions/{session_id}/access", response_model=SessionAccessResponse)
async def session_access(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> SessionAccessResponse:
    session = await session_service.get_access(current_user, session_id, is_admin=False)
    return SessionAccessResponse(notebookUrl=session.notebook_url)
