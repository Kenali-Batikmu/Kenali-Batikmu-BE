from __future__ import annotations

from datetime import timedelta
from typing import Any

from supabase import Client

from ..config import Settings
from ..domain import utcnow
from ..security import create_access_token, hash_token, new_refresh_token


def issue_tokens(db: Client, settings: Settings, user_id: int) -> dict[str, Any]:
    access, expires_in = create_access_token(user_id, settings)
    refresh = new_refresh_token()
    now = utcnow()

    # bersihkan token kedaluwarsa milik user ini agar tabel tidak menumpuk
    db.table("refresh_tokens").delete().eq("user_id", user_id).lt("expires_at", now.isoformat()).execute()
    db.table("refresh_tokens").insert(
        {
            "user_id": user_id,
            "token_hash": hash_token(refresh),  # hanya hash yang disimpan
            "expires_at": (now + timedelta(days=settings.refresh_token_days)).isoformat(),
            "created_at": now.isoformat(),
        }
    ).execute()
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer", "expires_in": expires_in}


def revoke_all_refresh_tokens(db: Client, user_id: int) -> None:
    db.table("refresh_tokens").update({"revoked_at": utcnow().isoformat()}).eq("user_id", user_id).is_(
        "revoked_at", "null"
    ).execute()
