from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from supabase import Client

from ..database import first
from ..domain import merge_progress

PROGRESS_TABLE = "user_module_progress"
PROGRESS_COLUMNS = (
    "module_id,status,progress_percent,history_done,character_done,gallery_done,quiz_done,practice_done,"
    "quiz_score,practice_score,passing_score,is_passed,completed_at,last_accessed_at,synced_at"
)
ATTEMPT_COLUMNS = "id,module_id,score,passed,total_questions,attempted_at,client_ref,synced_at"
PRACTICE_COLUMNS = "id,module_id,scan_type,top_motif_id,image_path,confidence,fit_score,passed,created_at,synced_at"


def list_progress(db: Client, user_id: int, since: datetime | None = None) -> list[dict[str, Any]]:
    q = db.table(PROGRESS_TABLE).select(PROGRESS_COLUMNS).eq("user_id", user_id)
    if since is not None:
        q = q.gt("synced_at", since.isoformat())
    return q.order("module_id").execute().data or []


def list_quiz_attempts(
    db: Client,
    user_id: int,
    module_id: int | None = None,
    since: datetime | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    q = db.table("quiz_attempts").select(ATTEMPT_COLUMNS).eq("user_id", user_id)
    if module_id is not None:
        q = q.eq("module_id", module_id)
    if since is not None:
        q = q.gt("synced_at", since.isoformat())
    return q.order("id", desc=True).limit(limit).execute().data or []


def list_practice_results(
    db: Client,
    user_id: int,
    module_id: int | None = None,
    since: datetime | None = None,
) -> list[dict[str, Any]]:
    q = db.table("scans").select(PRACTICE_COLUMNS).eq("user_id", user_id).eq("scan_type", "kuismu")
    if module_id is not None:
        q = q.eq("module_id", module_id)
    if since is not None:
        q = q.gt("synced_at", since.isoformat())
    return q.order("module_id").execute().data or []


def merge_and_save_progress(
    db: Client,
    user_id: int,
    module_id: int,
    incoming: Mapping[str, Any],
    passing_score: int,
    now: datetime,
) -> dict[str, Any]:
    """Baca progres server, gabungkan dengan kiriman klien, simpan (upsert per user+modul)."""
    existing = first(
        db.table(PROGRESS_TABLE).select("*").eq("user_id", user_id).eq("module_id", module_id).limit(1).execute()
    )
    row = merge_progress(existing, incoming, passing_score, now)
    row["user_id"] = user_id
    row["module_id"] = module_id
    db.table(PROGRESS_TABLE).upsert(row, on_conflict="user_id,module_id").execute()
    return row
