from __future__ import annotations

from urllib.parse import urlparse


def _normalize_origin(value: str) -> str | None:
    parsed = urlparse(value.strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    if not parsed.netloc:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def is_allowed_ws_origin(origin: str | None, allowed_origins: list[str]) -> bool:
    if origin is None:
        return True

    normalized_origin = _normalize_origin(origin)
    if normalized_origin is None:
        return False

    normalized_allowed: set[str] = set()
    for raw_origin in allowed_origins:
        if raw_origin == "*":
            return True
        normalized = _normalize_origin(raw_origin)
        if normalized:
            normalized_allowed.add(normalized)

    return normalized_origin in normalized_allowed
