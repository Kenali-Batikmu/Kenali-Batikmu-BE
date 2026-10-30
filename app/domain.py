"""Logika murni (tanpa database/jaringan) agar mudah diuji.

Aturan di sini meniru aplikasi mobile (module_dao.dart / quiz_dao.dart):
- Progres modul = 5 komponen x 20%: sejarah, karakteristik, galeri, kuis teori, praktikum.
- Kuis teori & praktikum hanya menyumbang 20% bila skor >= KKM (passing_score).
- Penggabungan data offline bersifat monoton: boolean di-OR, skor diambil yang tertinggi.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

POINTS_PER_COMPONENT = 20


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: Any) -> datetime | None:
    """Ubah string ISO-8601 / datetime menjadi datetime UTC (aware). None bila tidak valid."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def clamp_ts(value: Any, now: datetime, max_future_seconds: int = 300) -> datetime:
    """Waktu dari klien: kosong/tidak valid/di masa depan -> pakai waktu server."""
    dt = parse_ts(value)
    if dt is None or dt > now + timedelta(seconds=max_future_seconds):
        return now
    return dt


def normalize_confidence(value: float) -> tuple[float, int]:
    """Terima 0..1 atau 0..100. Kembalikan (0..1, skor bulat 0..100) seperti aplikasi."""
    v = float(value)
    if v > 1.0:
        v = v / 100.0
    v = min(max(v, 0.0), 1.0)
    return v, int(math.floor(v * 100 + 0.5))


def calc_progress(
    *,
    history_done: bool,
    character_done: bool,
    gallery_done: bool,
    quiz_done: bool,
    quiz_score: int | None,
    practice_done: bool,
    practice_score: int | None,
    passing_score: int,
) -> tuple[int, str, bool]:
    """Kembalikan (progress_percent, status, is_passed)."""
    completed = int(bool(history_done)) + int(bool(character_done)) + int(bool(gallery_done))
    if quiz_done and (quiz_score or 0) >= passing_score:
        completed += 1
    if practice_done and (practice_score or 0) >= passing_score:
        completed += 1
    percent = min(100, completed * POINTS_PER_COMPONENT)
    if percent >= 100:
        status = "completed"
    elif percent > 0:
        status = "in_progress"
    else:
        status = "not_started"
    return percent, status, percent >= 100


def _max_score(a: Any, b: Any) -> int | None:
    values = [int(v) for v in (a, b) if v is not None]
    return max(values) if values else None


def merge_progress(
    existing: Mapping[str, Any] | None,
    incoming: Mapping[str, Any],
    passing_score: int,
    now: datetime,
) -> dict[str, Any]:
    """Gabungkan progres server (existing) dengan kiriman klien (incoming).

    Hasilnya tidak pernah menurun, jadi aman dikirim ulang berkali-kali dan
    urutan sinkronisasi dari beberapa perangkat tidak menjadi masalah.
    """
    ex = existing or {}

    def flag(key: str) -> bool:
        return bool(ex.get(key)) or bool(incoming.get(key))

    history = flag("history_done")
    character = flag("character_done")
    gallery = flag("gallery_done")
    quiz_score = _max_score(ex.get("quiz_score"), incoming.get("quiz_score"))
    practice_score = _max_score(ex.get("practice_score"), incoming.get("practice_score"))
    quiz_done = flag("quiz_done") or quiz_score is not None
    practice_done = flag("practice_done") or practice_score is not None

    percent, status, is_passed = calc_progress(
        history_done=history,
        character_done=character,
        gallery_done=gallery,
        quiz_done=quiz_done,
        quiz_score=quiz_score,
        practice_done=practice_done,
        practice_score=practice_score,
        passing_score=passing_score,
    )

    completed_at = ex.get("completed_at")
    if is_passed and not completed_at:
        completed_at = now.isoformat()

    candidates = [parse_ts(ex.get("last_accessed_at")), clamp_ts(incoming.get("last_accessed_at"), now)]
    last_accessed = max(c for c in candidates if c is not None)

    return {
        "status": status,
        "progress_percent": percent,
        "history_done": history,
        "character_done": character,
        "gallery_done": gallery,
        "quiz_done": quiz_done,
        "practice_done": practice_done,
        "quiz_score": quiz_score,
        "practice_score": practice_score,
        "passing_score": passing_score,
        "is_passed": is_passed,
        "completed_at": completed_at,
        "last_accessed_at": last_accessed.isoformat(),
        "synced_at": now.isoformat(),
    }


def detect_image_type(data: bytes) -> tuple[str, str] | None:
    """Deteksi JPEG/PNG dari byte awal (tidak percaya header Content-Type dari klien)."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpg", "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png", "image/png"
    return None
