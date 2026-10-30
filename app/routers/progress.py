from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile
from supabase import Client

from ..config import Settings, get_settings
from ..database import get_db
from ..deps import get_current_user_id
from ..schemas import ImageUploadOut, PracticeOut, ProgressOut, QuizAttemptOut
from ..services.modules import get_module
from ..services.progress import list_practice_results, list_progress, list_quiz_attempts
from ..storage import ImageRejected, store_public_image

router = APIRouter(tags=["progres"])


@router.get("/progress", response_model=list[ProgressOut])
def get_progress(user_id: int = Depends(get_current_user_id), db: Client = Depends(get_db)):
    """Progres membaca modul + skor kuis teori + skor praktikum untuk semua modul milik pengguna."""
    return list_progress(db, user_id)


@router.get("/quiz/attempts", response_model=list[QuizAttemptOut])
def get_quiz_attempts(
    module_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=200, ge=1, le=1000),
    user_id: int = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Riwayat nilai kuis teori (terbaru lebih dulu)."""
    return list_quiz_attempts(db, user_id, module_id=module_id, limit=limit)


@router.get("/practice", response_model=list[PracticeOut])
def get_practice(
    module_id: int | None = Query(default=None, ge=1),
    user_id: int = Depends(get_current_user_id),
    db: Client = Depends(get_db),
):
    """Hasil praktikum (1 hasil terbaru per modul)."""
    return list_practice_results(db, user_id, module_id=module_id)


@router.put("/practice/{module_id}/image", response_model=ImageUploadOut)
def upload_practice_image(
    module_id: int = Path(ge=1),
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Client = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Unggah foto hasil praktikum. Pakai `image_url` yang dikembalikan sebagai `image_path` saat sync."""
    if get_module(db, module_id) is None:
        raise HTTPException(status_code=404, detail="Modul tidak ditemukan.")
    data = file.file.read(settings.max_upload_bytes + 1)
    try:
        url = store_public_image(
            db, settings.practices_bucket, str(user_id), f"module_{module_id}", data, settings.max_upload_bytes
        )
    except ImageRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    return ImageUploadOut(image_url=url)
