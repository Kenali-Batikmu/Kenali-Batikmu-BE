from __future__ import annotations

from typing import Any

from supabase import Client

from ..database import first

PUBLIC_COLUMNS = "id,name,email,phone,profile_image_path,created_at"
_PUBLIC_KEYS = ("id", "name", "email", "phone", "profile_image_path", "created_at")


def public_user(row: dict[str, Any]) -> dict[str, Any]:
    return {k: row.get(k) for k in _PUBLIC_KEYS}


def get_by_email(db: Client, email: str, columns: str = PUBLIC_COLUMNS) -> dict[str, Any] | None:
    return first(db.table("users").select(columns).eq("email", email).limit(1).execute())


def get_by_id(db: Client, user_id: int, columns: str = PUBLIC_COLUMNS) -> dict[str, Any] | None:
    return first(db.table("users").select(columns).eq("id", user_id).limit(1).execute())
