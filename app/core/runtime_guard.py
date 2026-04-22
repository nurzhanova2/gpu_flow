from __future__ import annotations

from app.config import Settings


_INSECURE_JWT_SECRETS = {
    "",
    "dev-secret",
    "dev-secret-change-me",
    "change-this-secret",
}


def validate_runtime_safety(settings: Settings) -> None:
    if not settings.strict_production_checks:
        return

    app_env = settings.app_env.strip().lower()
    if app_env not in {"prod", "production"}:
        return

    issues: list[str] = []

    if settings.jwt_secret in _INSECURE_JWT_SECRETS or len(settings.jwt_secret) < 32:
        issues.append("JWT_SECRET is weak. Use a strong random secret (>=32 chars).")
    if settings.seed_on_startup:
        issues.append("SEED_ON_STARTUP must be false in production.")
    if settings.slurm_mode == "mock":
        issues.append("SLURM_MODE cannot be 'mock' in production.")
    if settings.jupyterhub_mode == "mock":
        issues.append("JUPYTERHUB_MODE cannot be 'mock' in production.")
    if settings.metrics_mode == "mock":
        issues.append("METRICS_MODE cannot be 'mock' in production.")
    if settings.allow_user_registration:
        issues.append("ALLOW_USER_REGISTRATION must be false in production unless explicitly required.")
    if not settings.cors_allow_origins:
        issues.append("CORS_ALLOW_ORIGINS cannot be empty in production.")
    if "*" in settings.cors_allow_origins:
        issues.append("CORS_ALLOW_ORIGINS cannot contain '*' in production.")

    if issues:
        formatted = "\n".join(f"- {issue}" for issue in issues)
        raise RuntimeError(f"Unsafe production configuration detected:\n{formatted}")
