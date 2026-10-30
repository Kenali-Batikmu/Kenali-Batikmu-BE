from __future__ import annotations

from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from .config import get_settings


@lru_cache(maxsize=1)
def get_db() -> Client:
    """Klien Supabase dengan service_role key. Hanya dipakai di server, jangan pernah dikirim ke aplikasi."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def first(response: Any) -> dict[str, Any] | None:
    """Baris pertama dari hasil query supabase-py, atau None bila kosong."""
    rows = getattr(response, "data", None) or []
    return rows[0] if rows else None


def is_unique_violation(exc: Exception) -> bool:
    text = str(exc).lower()
    return "23505" in text or "duplicate key" in text
