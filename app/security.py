"""Hash password (scrypt), token JWT, dan decorator autentikasi."""
import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from functools import wraps

# pyrefly: ignore [missing-import]
import jwt
from flask import current_app, g, request

from .db import get_db
from .errors import ApiError

# Parameter scrypt (OWASP: N=2^15 lebih ketat; 2^14 cukup untuk server kecil).
_N, _R, _P, _DKLEN = 2**14, 8, 1, 32


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, dk_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(dk_b64)
        dk = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk, expected)


# Hash tiruan: dipakai agar waktu respons login email-tak-terdaftar mirip email-terdaftar.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def verify_dummy(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


# --- waktu ----------------------------------------------------------------
def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_iso() -> str:
    return iso(utcnow())


def parse_iso(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


# --- JWT ------------------------------------------------------------------
def create_token(user_id: int, remember: bool = False) -> tuple[str, int]:
    cfg = current_app.config
    ttl = timedelta(days=cfg["TOKEN_TTL_REMEMBER_DAYS"]) if remember else timedelta(hours=cfg["TOKEN_TTL_HOURS"])
    now = utcnow()
    payload = {"sub": str(user_id), "iat": now, "exp": now + ttl}
    token = jwt.encode(payload, cfg["SECRET_KEY"], algorithm="HS256")
    return token, int(ttl.total_seconds())


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise ApiError(401, "unauthorized", "Token autentikasi tidak ditemukan.")
        try:
            payload = jwt.decode(
                token,
                current_app.config["SECRET_KEY"],
                algorithms=["HS256"],
                options={"require": ["exp", "sub"]},
            )
            user_id = int(payload["sub"])
        except jwt.ExpiredSignatureError:
            raise ApiError(401, "token_expired", "Sesi berakhir, silakan login kembali.")
        except (jwt.InvalidTokenError, ValueError):
            raise ApiError(401, "invalid_token", "Token tidak valid.")

        user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            raise ApiError(401, "invalid_token", "Akun tidak ditemukan.")
        g.user = user
        return fn(*args, **kwargs)

    return wrapper
