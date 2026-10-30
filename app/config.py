from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Variabel lingkungan {name} harus berupa angka bulat.") from exc


@dataclass(frozen=True)
class Settings:
    # --- Supabase ---
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # --- Token ---
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 30

    # --- Keamanan login ---
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    # --- Lupa sandi (OTP) ---
    otp_length: int = 4  # sama dengan 4 kotak OTP di aplikasi mobile
    otp_ttl_minutes: int = 5
    otp_verified_ttl_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_seconds: int = 60

    # --- Email (SMTP) ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    app_name: str = "Kenali Batikmu"
    # HANYA untuk pengembangan: mengembalikan OTP di respons API.
    expose_otp_in_response: bool = False

    # --- Lain-lain ---
    cors_origins: tuple[str, ...] = ()
    avatars_bucket: str = "avatars"
    practices_bucket: str = "practices"
    max_upload_bytes: int = 5 * 1024 * 1024

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and (self.smtp_from or self.smtp_user))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    jwt_secret = os.getenv("JWT_SECRET", "").strip()

    missing = [
        name
        for name, value in (
            ("SUPABASE_URL", url),
            ("SUPABASE_SERVICE_ROLE_KEY", service_key),
            ("JWT_SECRET", jwt_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Variabel lingkungan wajib belum diisi: " + ", ".join(missing) + ". Salin .env.example menjadi .env."
        )
    if len(jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET minimal 32 karakter. Buat dengan: python -c \"import secrets; print(secrets.token_urlsafe(48))\"")

    origins = tuple(o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip())

    return Settings(
        supabase_url=url,
        supabase_service_role_key=service_key,
        jwt_secret=jwt_secret,
        access_token_minutes=_as_int("ACCESS_TOKEN_MINUTES", 30),
        refresh_token_days=_as_int("REFRESH_TOKEN_DAYS", 30),
        max_failed_logins=_as_int("MAX_FAILED_LOGINS", 5),
        lockout_minutes=_as_int("LOCKOUT_MINUTES", 15),
        otp_length=_as_int("OTP_LENGTH", 4),
        otp_ttl_minutes=_as_int("OTP_TTL_MINUTES", 5),
        smtp_host=os.getenv("SMTP_HOST", "").strip(),
        smtp_port=_as_int("SMTP_PORT", 587),
        smtp_user=os.getenv("SMTP_USER", "").strip(),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_from=os.getenv("SMTP_FROM", "").strip(),
        app_name=os.getenv("APP_NAME", "Kenali Batikmu").strip() or "Kenali Batikmu",
        expose_otp_in_response=_as_bool(os.getenv("EXPOSE_OTP_IN_RESPONSE")),
        cors_origins=origins,
    )
