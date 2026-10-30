from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not _EMAIL_RE.match(value):
        raise ValueError("Format email tidak valid")
    return value


# ====================================================================== AUTH

class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama lengkap wajib diisi")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _clean_email(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v is not None else None


class LoginIn(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _clean_email(v)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=300)


class ForgotPasswordIn(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _clean_email(v)


class VerifyOtpIn(BaseModel):
    email: str
    otp: str = Field(min_length=3, max_length=10, pattern=r"^\d+$")

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _clean_email(v)


class ResetPasswordIn(BaseModel):
    reset_token: str = Field(min_length=10, max_length=300)
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str
    email: str
    phone: str | None = None
    profile_image_path: str | None = None
    created_at: str | None = None


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthOut(TokenOut):
    user: UserOut


class MessageOut(BaseModel):
    message: str


class ForgotPasswordOut(BaseModel):
    message: str
    dev_otp: str | None = None  # hanya terisi bila EXPOSE_OTP_IN_RESPONSE=true (pengembangan)


class VerifyOtpOut(BaseModel):
    reset_token: str


# ====================================================================== PROFIL

class UpdateProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = None
    current_password: str | None = Field(default=None, max_length=128)  # wajib bila mengganti email

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Nama tidak boleh kosong")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        return _clean_email(v) if v is not None else None


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ImageUploadOut(BaseModel):
    image_url: str


# ====================================================================== PROGRES (baca)
# Nama field sengaja sama dengan kolom tabel Supabase yang sudah dipakai aplikasi.

class ProgressOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    module_id: int
    status: str = "not_started"
    progress_percent: int = 0
    history_done: bool = False
    character_done: bool = False
    gallery_done: bool = False
    quiz_done: bool = False
    practice_done: bool = False
    quiz_score: int | None = None
    practice_score: int | None = None
    passing_score: int = 70
    is_passed: bool = False
    completed_at: str | None = None
    last_accessed_at: str | None = None
    synced_at: str | None = None


class QuizAttemptOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    module_id: int
    score: int
    passed: bool
    total_questions: int | None = None
    attempted_at: str | None = None
    client_ref: str | None = None
    synced_at: str | None = None


class PracticeOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    module_id: int
    scan_type: str = "kuismu"
    top_motif_id: int | None = None
    image_path: str | None = None
    confidence: float | None = None
    fit_score: float | None = None
    passed: bool | None = None
    created_at: str | None = None
    synced_at: str | None = None


# ====================================================================== SINKRONISASI

class ProgressPush(BaseModel):
    module_id: int = Field(ge=1)
    history_done: bool = False
    character_done: bool = False
    gallery_done: bool = False
    quiz_done: bool = False
    practice_done: bool = False
    quiz_score: int | None = Field(default=None, ge=0, le=100)
    practice_score: int | None = Field(default=None, ge=0, le=100)
    last_accessed_at: datetime | None = None


class QuizAttemptPush(BaseModel):
    module_id: int = Field(ge=1)
    score: int = Field(ge=0, le=100)
    total_questions: int | None = Field(default=None, ge=1, le=1000)
    attempted_at: datetime | None = None
    # ID unik dari perangkat (mis. "<device>-<id lokal>") supaya kirim ulang tidak menggandakan data.
    client_ref: str | None = Field(default=None, min_length=1, max_length=100)


class PracticePush(BaseModel):
    module_id: int = Field(ge=1)
    confidence: float = Field(ge=0, le=100)  # 0..1 atau 0..100
    image_path: str | None = Field(default=None, max_length=1000)  # URL dari PUT /practice/{id}/image
    inference_time_ms: int | None = Field(default=None, ge=0, le=600000)
    created_at: datetime | None = None


class SyncPushIn(BaseModel):
    # Item sengaja diterima mentah dan divalidasi SATU PER SATU di services/sync.py (terhadap
    # ProgressPush / QuizAttemptPush / PracticePush). Bila divalidasi di tingkat request, satu item
    # cacat membuat seluruh batch ditolak (422) dan item itu tertahan selamanya di antrean aplikasi.
    progress: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    quiz_attempts: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    practice_results: list[dict[str, Any]] = Field(default_factory=list, max_length=100)


class ItemResult(BaseModel):
    index: int
    module_id: int | None = None
    client_ref: str | None = None
    # accepted/duplicate/rejected -> aman ditandai is_synced=1.  error -> sementara, kirim ulang nanti.
    status: Literal["accepted", "duplicate", "rejected", "error"]
    detail: str | None = None


class SyncPushOut(BaseModel):
    server_time: str
    progress: list[ItemResult]
    quiz_attempts: list[ItemResult]
    practice_results: list[ItemResult]
    progress_snapshot: list[ProgressOut]  # progres hasil gabungan di server, untuk menimpa data lokal


class SyncPullOut(BaseModel):
    server_time: str
    progress: list[ProgressOut]
    quiz_attempts: list[QuizAttemptOut]
    practice_results: list[PracticeOut]
