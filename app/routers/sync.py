from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from supabase import Client

from ..database import get_db
from ..deps import get_current_user_id
from ..domain import utcnow
from ..schemas import SyncPullOut, SyncPushIn, SyncPushOut
from ..services.progress import list_practice_results, list_progress, list_quiz_attempts
from ..services.sync import process_push

router = APIRouter(prefix="/sync", tags=["sinkronisasi"])


@router.get("/pull", response_model=SyncPullOut)
def pull(
    since: datetime | None = Query(
        default=None, description="ISO-8601 UTC (mis. 2026-10-27T03:00:00Z). Kosong = ambil semuanya."
    ),
    attempt_limit: int = Query(default=500, ge=1, le=2000),
    user_id: int = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Satu panggilan setelah login: progres modul, riwayat kuis teori, dan hasil praktikum.

    Simpan `server_time` dan kirim sebagai `since` pada tarikan berikutnya untuk data tambahan saja.
    """
    now = utcnow()
    return {
        "server_time": now.isoformat(),
        "progress": list_progress(db, user_id, since),
        "quiz_attempts": list_quiz_attempts(db, user_id, since=since, limit=attempt_limit),
        "practice_results": list_practice_results(db, user_id, since=since),
    }


@router.post("/push", response_model=SyncPushOut)
def push(body: SyncPushIn, user_id: int = Depends(get_current_user_id), db: Client = Depends(get_db)):
    """Kirim antrean offline (progres, kuis teori, praktikum). Hasil dilaporkan per item."""
    return process_push(db, user_id, body, utcnow())
