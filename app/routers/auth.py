from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from supabase import Client

from ..config import Settings, get_settings
from ..database import first, get_db, is_unique_violation
from ..domain import parse_ts, utcnow
from ..mailer import send_otp_email
from ..schemas import (
    AuthOut,
    ForgotPasswordIn,
    ForgotPasswordOut,
    LoginIn,
    MessageOut,
    RefreshIn,
    RegisterIn,
    ResetPasswordIn,
    TokenOut,
    UserOut,
    VerifyOtpIn,
    VerifyOtpOut,
)
from ..security import (
    constant_time_equal,
    create_access_token,
    generate_otp,
    hash_otp,
    hash_password,
    hash_token,
    needs_rehash,
    verify_password,
)
from ..services.auth_tokens import issue_tokens, revoke_all_refresh_tokens
from ..services.users import PUBLIC_COLUMNS, get_by_email, public_user

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger("kenali.auth")

# Dipakai agar waktu respons login tidak membocorkan apakah email terdaftar.
_DUMMY_HASH = hash_password("kenali-dummy-password")
_BAD_LOGIN = "Email atau kata sandi salah."
_GENERIC_FORGOT = "Jika email terdaftar, kode verifikasi telah dikirim."


def _auth_response(db: Client, settings: Settings, user_row: dict) -> AuthOut:
    tokens = issue_tokens(db, settings, int(user_row["id"]))
    return AuthOut(user=UserOut(**public_user(user_row)), **tokens)


@router.post("/register", response_model=AuthOut, status_code=201)
def register(body: RegisterIn, db: Client = Depends(get_db), settings: Settings = Depends(get_settings)):
    if get_by_email(db, body.email, "id"):
        raise HTTPException(status_code=409, detail="Email sudah terdaftar.")
    now = utcnow().isoformat()
    try:
        res = db.table("users").insert(
            {
                "name": body.name,
                "email": body.email,
                "phone": body.phone,
                "password_hash": hash_password(body.password),
                "created_at": now,
                "updated_at": now,
            }
        ).execute()
    except Exception as exc:  # noqa: BLE001
        if is_unique_violation(exc):
            raise HTTPException(status_code=409, detail="Email sudah terdaftar.")
        raise
    row = first(res)
    if row is None:
        raise HTTPException(status_code=500, detail="Gagal membuat akun.")
    return _auth_response(db, settings, row)


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, db: Client = Depends(get_db), settings: Settings = Depends(get_settings)):
    user = get_by_email(db, body.email, PUBLIC_COLUMNS + ",password_hash,failed_attempts,lockout_until")
    if user is None:
        verify_password(body.password, _DUMMY_HASH)
        raise HTTPException(status_code=401, detail=_BAD_LOGIN)

    now = utcnow()
    locked_until = parse_ts(user.get("lockout_until"))
    if locked_until and locked_until > now:
        retry_after = int((locked_until - now).total_seconds()) + 1
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak percobaan gagal. Coba lagi beberapa menit lagi.",
            headers={"Retry-After": str(retry_after)},
        )

    if not verify_password(body.password, user.get("password_hash")):
        attempts = int(user.get("failed_attempts") or 0) + 1
        patch: dict = {"failed_attempts": attempts}
        if attempts >= settings.max_failed_logins:
            patch = {
                "failed_attempts": 0,
                "lockout_until": (now + timedelta(minutes=settings.lockout_minutes)).isoformat(),
            }
        db.table("users").update(patch).eq("id", user["id"]).execute()
        raise HTTPException(status_code=401, detail=_BAD_LOGIN)

    patch = {}
    if user.get("failed_attempts") or user.get("lockout_until"):
        patch.update({"failed_attempts": 0, "lockout_until": None})
    if needs_rehash(user.get("password_hash")):
        patch["password_hash"] = hash_password(body.password)  # upgrade hash SHA-256 lama -> scrypt
    if patch:
        db.table("users").update(patch).eq("id", user["id"]).execute()

    return _auth_response(db, settings, user)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Client = Depends(get_db), settings: Settings = Depends(get_settings)):
    """Tukar refresh token dengan access token baru.

    Refresh token tidak dirotasi (agar aman bila respons hilang di jaringan buruk),
    tetapi masa berlakunya diperpanjang tiap dipakai dan bisa dicabut lewat /auth/logout.
    """
    now = utcnow()
    rec = first(
        db.table("refresh_tokens")
        .select("id,user_id,expires_at,revoked_at")
        .eq("token_hash", hash_token(body.refresh_token))
        .limit(1)
        .execute()
    )
    expires_at = parse_ts(rec["expires_at"]) if rec else None
    if rec is None or rec.get("revoked_at") or expires_at is None or expires_at <= now:
        raise HTTPException(status_code=401, detail="Sesi berakhir. Silakan masuk kembali.")

    db.table("refresh_tokens").update(
        {"expires_at": (now + timedelta(days=settings.refresh_token_days)).isoformat(), "last_used_at": now.isoformat()}
    ).eq("id", rec["id"]).execute()
    access, expires_in = create_access_token(int(rec["user_id"]), settings)
    return TokenOut(access_token=access, refresh_token=body.refresh_token, expires_in=expires_in)


@router.post("/logout", status_code=204)
def logout(body: RefreshIn, db: Client = Depends(get_db)):
    db.table("refresh_tokens").update({"revoked_at": utcnow().isoformat()}).eq(
        "token_hash", hash_token(body.refresh_token)
    ).is_("revoked_at", "null").execute()
    return Response(status_code=204)


# ------------------------------------------------------------------ lupa sandi (3 langkah)

def _bad_otp() -> HTTPException:
    return HTTPException(status_code=400, detail="Kode verifikasi salah atau sudah kedaluwarsa.")


@router.post("/forgot-password", response_model=ForgotPasswordOut, status_code=202)
def forgot_password(
    body: ForgotPasswordIn,
    background: BackgroundTasks,
    db: Client = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Langkah 1. Respons selalu sama, terlepas email terdaftar atau tidak."""
    out = ForgotPasswordOut(message=_GENERIC_FORGOT)
    user = get_by_email(db, body.email, "id,name,email")
    if user is None:
        return out

    now = utcnow()
    uid = int(user["id"])
    last = first(
        db.table("password_resets")
        .select("created_at")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    last_at = parse_ts(last["created_at"]) if last else None
    if last_at and (now - last_at).total_seconds() < settings.otp_resend_seconds:
        return out  # cegah spam email

    otp = generate_otp(settings.otp_length)
    db.table("password_resets").update({"used_at": now.isoformat()}).eq("user_id", uid).is_("used_at", "null").execute()
    db.table("password_resets").insert(
        {
            "user_id": uid,
            "otp_hash": hash_otp(otp, uid, settings.jwt_secret),
            "attempts": 0,
            "verified": False,
            "expires_at": (now + timedelta(minutes=settings.otp_ttl_minutes)).isoformat(),
            "created_at": now.isoformat(),
        }
    ).execute()

    background.add_task(send_otp_email, settings, user["email"], user.get("name") or "", otp)
    if settings.expose_otp_in_response:
        out.dev_otp = otp
    return out


@router.post("/verify-otp", response_model=VerifyOtpOut)
def verify_otp(body: VerifyOtpIn, db: Client = Depends(get_db), settings: Settings = Depends(get_settings)):
    """Langkah 2. Menukar OTP yang benar dengan reset_token sekali pakai."""
    user = get_by_email(db, body.email, "id")
    if user is None:
        raise _bad_otp()
    uid = int(user["id"])
    now = utcnow()

    rec = first(
        db.table("password_resets")
        .select("id,otp_hash,attempts,verified,expires_at")
        .eq("user_id", uid)
        .is_("used_at", "null")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    expires_at = parse_ts(rec["expires_at"]) if rec else None
    if (
        rec is None
        or rec.get("verified")
        or expires_at is None
        or expires_at <= now
        or int(rec.get("attempts") or 0) >= settings.otp_max_attempts
    ):
        raise _bad_otp()

    if not constant_time_equal(hash_otp(body.otp, uid, settings.jwt_secret), rec["otp_hash"]):
        db.table("password_resets").update({"attempts": int(rec.get("attempts") or 0) + 1}).eq("id", rec["id"]).execute()
        raise _bad_otp()

    reset_token = secrets.token_urlsafe(32)
    db.table("password_resets").update(
        {
            "verified": True,
            "reset_token_hash": hash_token(reset_token),
            "expires_at": (now + timedelta(minutes=settings.otp_verified_ttl_minutes)).isoformat(),
        }
    ).eq("id", rec["id"]).execute()
    return VerifyOtpOut(reset_token=reset_token)


@router.post("/reset-password", response_model=MessageOut)
def reset_password(body: ResetPasswordIn, db: Client = Depends(get_db)):
    """Langkah 3. Pasang sandi baru dan cabut semua sesi lama."""
    now = utcnow()
    rec = first(
        db.table("password_resets")
        .select("id,user_id,expires_at")
        .eq("reset_token_hash", hash_token(body.reset_token))
        .eq("verified", "true")
        .is_("used_at", "null")
        .limit(1)
        .execute()
    )
    expires_at = parse_ts(rec["expires_at"]) if rec else None
    if rec is None or expires_at is None or expires_at <= now:
        raise HTTPException(status_code=400, detail="Sesi pemulihan tidak valid atau sudah berakhir.")

    uid = int(rec["user_id"])
    db.table("users").update(
        {
            "password_hash": hash_password(body.new_password),
            "failed_attempts": 0,
            "lockout_until": None,
            "updated_at": now.isoformat(),
        }
    ).eq("id", uid).execute()
    db.table("password_resets").update({"used_at": now.isoformat()}).eq("id", rec["id"]).execute()
    revoke_all_refresh_tokens(db, uid)
    return MessageOut(message="Kata sandi berhasil diubah. Silakan masuk dengan kata sandi baru.")
