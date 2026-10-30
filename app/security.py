from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta, timezone

import jwt

from .config import Settings

# Format hash sama dengan data bawaan aplikasi: scrypt$N$r$p$salt_b64$hash_b64
_N, _R, _P, _DKLEN = 2**14, 8, 1, 32
_MAXMEM = 64 * 1024 * 1024

# Hash lama di aplikasi mobile: SHA-256("kenali_batikmu_salt_2026" + sandi). Hanya untuk migrasi.
_LEGACY_SALT = "kenali_batikmu_salt_2026"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN, maxmem=_MAXMEM)
    return "scrypt${}${}${}${}${}".format(
        _N, _R, _P, base64.b64encode(salt).decode(), base64.b64encode(digest).decode()
    )


def _is_legacy_sha256(stored: str) -> bool:
    return len(stored) == 64 and all(c in string.hexdigits for c in stored)


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    if stored.startswith("scrypt$"):
        try:
            _, n, r, p, salt_b64, hash_b64 = stored.split("$")
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(hash_b64)
            actual = hashlib.scrypt(
                password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected), maxmem=_MAXMEM
            )
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(actual, expected)
    if _is_legacy_sha256(stored):
        digest = hashlib.sha256((_LEGACY_SALT + password).encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest.lower(), stored.lower())
    return False


def needs_rehash(stored: str | None) -> bool:
    """True bila hash masih format lama (SHA-256) atau parameter scrypt berbeda."""
    return not (stored or "").startswith(f"scrypt${_N}${_R}${_P}$")


# ---------------------------------------------------------------- JWT

def create_access_token(user_id: int, settings: Settings, now: datetime | None = None) -> tuple[str, int]:
    now = now or datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": str(user_id), "type": "access", "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, settings.access_token_minutes * 60


def decode_access_token(token: str, settings: Settings) -> int:
    """Kembalikan user_id. Melempar jwt.PyJWTError bila token tidak valid/kedaluwarsa."""
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub"]},
        leeway=10,
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Jenis token salah")
    try:
        return int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise jwt.InvalidTokenError("Subjek token tidak valid") from exc


# ---------------------------------------------------------------- token acak & OTP

def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_otp(length: int) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))


def hash_otp(otp: str, user_id: int, secret: str) -> str:
    """HMAC (bukan hash polos) karena OTP hanya 4 digit dan mudah ditebak bila bocor."""
    return hmac.new(secret.encode("utf-8"), f"{user_id}:{otp}".encode("utf-8"), hashlib.sha256).hexdigest()


def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
