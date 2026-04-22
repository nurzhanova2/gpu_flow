import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field
from pydantic.functional_validators import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(default="sqlite+aiosqlite:///./gpuflow.db", alias="DATABASE_URL")

    jwt_secret: str = Field(default="dev-secret", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=720, alias="JWT_EXPIRE_MINUTES")
    login_max_attempts: int = Field(default=5, alias="LOGIN_MAX_ATTEMPTS")
    login_lockout_seconds: int = Field(default=300, alias="LOGIN_LOCKOUT_SECONDS")
    allow_user_registration: bool = Field(default=True, alias="ALLOW_USER_REGISTRATION")
    strict_production_checks: bool = Field(default=True, alias="STRICT_PRODUCTION_CHECKS")

    slurm_mode: str = Field(default="mock", alias="SLURM_MODE")
    jupyterhub_mode: str = Field(default="mock", alias="JUPYTERHUB_MODE")
    metrics_mode: str = Field(default="mock", alias="METRICS_MODE")

    queue_tick_seconds: int = Field(default=3, alias="QUEUE_TICK_SECONDS")
    session_tick_seconds: int = Field(default=4, alias="SESSION_TICK_SECONDS")
    workers_enabled: bool = Field(default=True, alias="WORKERS_ENABLED")
    workers_use_db_lock: bool = Field(default=True, alias="WORKERS_USE_DB_LOCK")
    queue_start_delay_seconds: int = Field(default=8, alias="QUEUE_START_DELAY_SECONDS")
    queue_start_timeout_seconds: int = Field(default=300, alias="QUEUE_START_TIMEOUT_SECONDS")
    session_idle_timeout_seconds: int = Field(default=120, alias="SESSION_IDLE_TIMEOUT_SECONDS")
    session_max_runtime_seconds: int = Field(default=2400, alias="SESSION_MAX_RUNTIME_SECONDS")
    ws_heartbeat_timeout_seconds: int = Field(default=45, alias="WS_HEARTBEAT_TIMEOUT_SECONDS")
    ws_auth_recheck_seconds: int = Field(default=30, alias="WS_AUTH_RECHECK_SECONDS")

    cluster_gpu_total: int = Field(default=3, alias="CLUSTER_GPU_TOTAL")
    default_max_active_sessions: int = Field(default=1, alias="DEFAULT_MAX_ACTIVE_SESSIONS")
    default_max_queued_requests: int = Field(default=2, alias="DEFAULT_MAX_QUEUED_REQUESTS")
    cors_allow_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        alias="CORS_ALLOW_ORIGINS",
    )

    seed_on_startup: bool = Field(default=True, alias="SEED_ON_STARTUP")
    seed_sync_existing_users: bool = Field(default=True, alias="SEED_SYNC_EXISTING_USERS")

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []

            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    pass

            return [item.strip() for item in raw.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
