import logging
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

log = logging.getLogger(__name__)


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _secret_key() -> str:
    key = os.environ.get("SECRET_KEY", "")
    if key and key != "ganti-dengan-string-acak-panjang":
        return key
    log.warning(
        "SECRET_KEY belum diset: memakai kunci acak sementara. Token login akan "
        "tidak valid setiap server restart. Set SECRET_KEY di .env untuk produksi."
    )
    return secrets.token_urlsafe(48)


class Config:
    SECRET_KEY = _secret_key()

    DATABASE = os.environ.get("DATABASE", str(Path(__file__).resolve().parent / "kenali_batikmu.db"))
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", str(BASE_DIR / "uploads"))

    MAX_CONTENT_LENGTH = _int("MAX_UPLOAD_MB", 16) * 1024 * 1024  # foto kamera HP bisa > 8 MB

    TOKEN_TTL_HOURS = _int("TOKEN_TTL_HOURS", 24)
    TOKEN_TTL_REMEMBER_DAYS = _int("TOKEN_TTL_REMEMBER_DAYS", 30)
    MIN_PASSWORD_LENGTH = 8
    MAX_FAILED_ATTEMPTS = _int("MAX_FAILED_ATTEMPTS", 5)
    LOCKOUT_MINUTES = _int("LOCKOUT_MINUTES", 15)

    CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

    AUTO_SEED = os.environ.get("AUTO_SEED", "1") == "1"
    # Akun demo yang dulu ada di app (sekar@batikmu.id, kenalibatikmu@gmail.com).
    # Password-nya publik: matikan (0) di produksi.
    SEED_DEMO_USERS = os.environ.get("SEED_DEMO_USERS", "0") == "1"

    # Lupa kata sandi (OTP 4 digit, sama dengan UI app)
    OTP_TTL_MINUTES = _int("OTP_TTL_MINUTES", 5)
    OTP_MAX_ATTEMPTS = _int("OTP_MAX_ATTEMPTS", 5)
    OTP_RESEND_SECONDS = _int("OTP_RESEND_SECONDS", 30)
    RESET_TOKEN_TTL_MINUTES = _int("RESET_TOKEN_TTL_MINUTES", 10)
    # Tanpa SMTP, OTP dikembalikan di respons API (mode demo, seperti "Mode Demo" di app).
    # WAJIB 0 di produksi.
    ALLOW_DEMO_OTP = os.environ.get("ALLOW_DEMO_OTP", "0") == "1"

    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = _int("SMTP_PORT", 587)
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_SECURITY = os.environ.get("SMTP_SECURITY", "starttls")  # starttls | ssl | none
    SMTP_FROM = os.environ.get("SMTP_FROM", "") or os.environ.get("SMTP_USER", "")

    SCORE_VERY_SIMILAR = 0.70
    SCORE_FAIRLY_SIMILAR = 0.50
    UNIVERSAL_PASS_THRESHOLD = 0.70
