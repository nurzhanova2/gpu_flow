from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_app_settings, get_current_user
from app.config import Settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import User, UserRole
from app.repositories.user_repo import UserRepository
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> TokenResponse:
    now = datetime.now(UTC)
    guard_key = f"{payload.username}:{request.client.host if request.client else 'unknown'}"
    try:
        await request.app.state.login_guard.assert_not_locked(guard_key)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": {"code": str(exc), "message": "Too many login attempts", "details": {}}},
        ) from exc

    user_repo = UserRepository(db)
    user = await user_repo.get_by_username_for_update(payload.username)

    if user and user.login_locked_until and user.login_locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": {"code": "AUTH_LOGIN_TEMPORARILY_BLOCKED", "message": "Too many login attempts", "details": {}}},
        )

    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.login_max_attempts:
                user.login_locked_until = now + timedelta(seconds=settings.login_lockout_seconds)
            await db.commit()
        await request.app.state.login_guard.register_failure(guard_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "AUTH_INVALID_CREDENTIALS", "message": "Invalid username/password", "details": {}}},
        )

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "AUTH_USER_BLOCKED", "message": "User is blocked", "details": {}}},
        )

    user.failed_login_attempts = 0
    user.login_locked_until = None
    await db.commit()
    await request.app.state.login_guard.register_success(guard_key)
    token = create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> TokenResponse:
    if not settings.allow_user_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "AUTH_REGISTRATION_DISABLED", "message": "Registration is disabled", "details": {}}},
        )

    user_repo = UserRepository(db)
    existing_username = await user_repo.get_by_username(payload.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "AUTH_USERNAME_EXISTS", "message": "Username already exists", "details": {}}},
        )

    existing_email = await user_repo.get_by_email(payload.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "AUTH_EMAIL_EXISTS", "message": "Email already exists", "details": {}}},
        )

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        email=payload.email,
        team=payload.team,
        password_hash=hash_password(payload.password),
        role=UserRole.user,
        max_active_sessions=settings.default_max_active_sessions,
        max_queued_requests=settings.default_max_queued_requests,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "AUTH_REGISTER_CONFLICT", "message": "Username or email already exists", "details": {}}},
        ) from exc
    await db.refresh(user)

    token = create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))


@router.get("/me", response_model=UserPublic)
async def me(current_user=Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current_user)
