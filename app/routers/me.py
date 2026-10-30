from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from supabase import Client

from ..config import Settings, get_settings
from ..database import get_db, is_unique_violation
from ..deps import get_current_user_id
from ..domain import utcnow
from ..schemas import AuthOut, ChangePasswordIn, UpdateProfileIn, UserOut
from ..security import hash_password, verify_password
from ..services.auth_tokens import issue_tokens, revoke_all_refresh_tokens
from ..services.users import PUBLIC_COLUMNS, get_by_email, get_by_id, public_user
from ..storage import ImageRejected, remove_images, store_public_image

router = APIRouter(prefix="/me", tags=["profil"])


def _current(db: Client, user_id: int, columns: str = PUBLIC_COLUMNS) -> dict:
    row = get_by_id(db, user_id, columns)
    if row is None:
        raise HTTPException(status_code=401, detail="Akun tidak ditemukan.")
    return row


@router.get("", response_model=UserOut)
def get_me(user_id: int = Depends(get_current_user_id), db: Client = Depends(get_db)):
    return UserOut(**public_user(_current(db, user_id)))


@router.patch("", response_model=UserOut)
def update_me(body: UpdateProfileIn, user_id: int = Depends(get_current_user_id), db: Client = Depends(get_db)):
    user = _current(db, user_id, PUBLIC_COLUMNS + ",password_hash")
    patch: dict = {}

    if body.name is not None:
        patch["name"] = body.name
    if "phone" in body.model_fields_set:
        patch["phone"] = (body.phone or "").strip() or None

    if body.email is not None and body.email != user["email"]:
        if not body.current_password or not verify_password(body.current_password, user.get("password_hash")):
            raise HTTPException(status_code=403, detail="Kata sandi saat ini diperlukan untuk mengganti email.")
        if get_by_email(db, body.email, "id"):
            raise HTTPException(status_code=409, detail="Email sudah dipakai akun lain.")
        patch["email"] = body.email

    if not patch:
        return UserOut(**public_user(user))

    patch["updated_at"] = utcnow().isoformat()
    try:
        db.table("users").update(patch).eq("id", user_id).execute()
    except Exception as exc:  # noqa: BLE001
        if is_unique_violation(exc):
            raise HTTPException(status_code=409, detail="Email sudah dipakai akun lain.")
        raise
    return UserOut(**public_user(_current(db, user_id)))


@router.post("/password", response_model=AuthOut)
def change_password(
    body: ChangePasswordIn,
    user_id: int = Depends(get_current_user_id),
    db: Client = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Ganti sandi, cabut semua sesi lama, dan kembalikan token baru untuk perangkat ini."""
    user = _current(db, user_id, PUBLIC_COLUMNS + ",password_hash")
    if not verify_password(body.current_password, user.get("password_hash")):
        raise HTTPException(status_code=403, detail="Kata sandi saat ini salah.")
    db.table("users").update(
        {"password_hash": hash_password(body.new_password), "updated_at": utcnow().isoformat()}
    ).eq("id", user_id).execute()
    revoke_all_refresh_tokens(db, user_id)
    tokens = issue_tokens(db, settings, user_id)
    return AuthOut(user=UserOut(**public_user(user)), **tokens)


@router.put("/avatar", response_model=UserOut)
def upload_avatar(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Client = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    data = file.file.read(settings.max_upload_bytes + 1)
    try:
        url = store_public_image(db, settings.avatars_bucket, str(user_id), "avatar", data, settings.max_upload_bytes)
    except ImageRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    db.table("users").update({"profile_image_path": url, "updated_at": utcnow().isoformat()}).eq("id", user_id).execute()
    return UserOut(**public_user(_current(db, user_id)))


@router.delete("/avatar", status_code=204)
def delete_avatar(
    user_id: int = Depends(get_current_user_id),
    db: Client = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    remove_images(db, settings.avatars_bucket, [f"{user_id}/avatar.jpg", f"{user_id}/avatar.png"])
    db.table("users").update({"profile_image_path": None, "updated_at": utcnow().isoformat()}).eq("id", user_id).execute()
    return Response(status_code=204)
