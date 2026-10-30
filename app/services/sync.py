from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable

from pydantic import ValidationError
from supabase import Client

from ..database import first
from ..domain import clamp_ts, normalize_confidence, parse_ts
from ..schemas import PracticePush, ProgressPush, QuizAttemptPush, SyncPushIn
from .modules import get_module
from .progress import list_progress, merge_and_save_progress

log = logging.getLogger("kenali.sync")

Outcome = tuple[str, str | None]  # (status, detail)


def record_progress(db: Client, user_id: int, item: ProgressPush, now: datetime) -> Outcome:
    module = get_module(db, item.module_id)
    if module is None:
        return "rejected", "module_id tidak dikenal"
    merge_and_save_progress(
        db, user_id, item.module_id, item.model_dump(), int(module["passing_score"]), now
    )
    return "accepted", None


def record_quiz_attempt(db: Client, user_id: int, item: QuizAttemptPush, now: datetime) -> Outcome:
    module = get_module(db, item.module_id)
    if module is None:
        return "rejected", "module_id tidak dikenal"
    passing = int(module["passing_score"])

    row = {
        "user_id": user_id,
        "module_id": item.module_id,
        "score": item.score,
        "passed": item.score >= passing,  # KKM dari server, bukan dari klien
        "total_questions": item.total_questions,
        "attempted_at": clamp_ts(item.attempted_at, now).isoformat(),
        "client_ref": item.client_ref,
        "synced_at": now.isoformat(),
    }
    res = (
        db.table("quiz_attempts")
        .upsert(row, on_conflict="user_id,client_ref", ignore_duplicates=True)
        .execute()
    )
    if item.client_ref and not res.data:
        return "duplicate", None  # client_ref ini sudah pernah diterima

    merge_and_save_progress(
        db, user_id, item.module_id, {"quiz_done": True, "quiz_score": item.score}, passing, now
    )
    return "accepted", None


def record_practice(db: Client, user_id: int, item: PracticePush, now: datetime) -> Outcome:
    module = get_module(db, item.module_id)
    if module is None:
        return "rejected", "module_id tidak dikenal"
    passing = int(module["passing_score"])

    confidence, score = normalize_confidence(item.confidence)
    created_at = clamp_ts(item.created_at, now)
    image = item.image_path if item.image_path and item.image_path.startswith(("http://", "https://")) else None

    existing = first(
        db.table("scans")
        .select("id,created_at")
        .eq("user_id", user_id)
        .eq("module_id", item.module_id)
        .eq("scan_type", "kuismu")
        .limit(1)
        .execute()
    )
    existing_at = parse_ts(existing["created_at"]) if existing else None

    status: str = "accepted"
    detail: str | None = None
    if existing_at is not None and existing_at > created_at:
        # Aplikasi menyimpan 1 hasil praktikum per modul (yang terbaru menang).
        status, detail = "duplicate", "Server sudah memiliki hasil praktikum yang lebih baru."
    else:
        row = {
            "scan_type": "kuismu",
            "module_id": item.module_id,
            "top_motif_id": module.get("motif_id"),
            "image_path": image,
            "confidence": confidence,
            "fit_score": confidence,
            "passed": score >= passing,
            "inference_time_ms": item.inference_time_ms,
            "created_at": created_at.isoformat(),
            "synced_at": now.isoformat(),
        }
        if existing:
            db.table("scans").update(row).eq("id", existing["id"]).execute()
        else:
            db.table("scans").insert({**row, "user_id": user_id}).execute()

    # Skor terbaik tetap dihitung ke progres modul walaupun foto lama tidak menimpa foto baru.
    merge_and_save_progress(
        db, user_id, item.module_id, {"practice_done": True, "practice_score": score}, passing, now
    )
    return status, detail


def _run(index: int, module_id: int | None, client_ref: str | None, fn: Callable[[], Outcome]) -> dict[str, Any]:
    try:
        status, detail = fn()
    except Exception:  # noqa: BLE001 - satu item gagal tidak boleh menggagalkan seluruh batch
        log.exception("Sinkronisasi item gagal (index=%s, module_id=%s)", index, module_id)
        status, detail = "error", "Kesalahan sementara di server, coba kirim ulang."
    return {"index": index, "module_id": module_id, "client_ref": client_ref, "status": status, "detail": detail}


def _validate(model: Any, raw: Any) -> tuple[Any, str | None]:
    """Validasi satu item. Kembalikan (item, None) atau (None, alasan singkat)."""
    try:
        return model.model_validate(raw), None
    except ValidationError as exc:
        err = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(part) for part in err.get("loc", ()))
        reason = f"{where}: {err.get('msg', 'tidak valid')}" if where else str(err.get("msg", "tidak valid"))
        return None, f"Item tidak valid ({reason})"


def _raw_field(raw: Any, key: str, kind: type) -> Any:
    value = raw.get(key) if isinstance(raw, dict) else None
    return value if isinstance(value, kind) and not isinstance(value, bool) else None


def _process(
    db: Client,
    user_id: int,
    now: datetime,
    raw_items: list[Any],
    model: Any,
    handler: Callable[..., Outcome],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_items):
        item, error = _validate(model, raw)
        if item is None:
            # Cacat permanen: 'rejected' agar aplikasi berhenti mengirim ulang item ini.
            results.append(
                {
                    "index": index,
                    "module_id": _raw_field(raw, "module_id", int),
                    "client_ref": _raw_field(raw, "client_ref", str),
                    "status": "rejected",
                    "detail": error,
                }
            )
            continue
        results.append(
            _run(
                index,
                item.module_id,
                getattr(item, "client_ref", None),
                lambda item=item: handler(db, user_id, item, now),
            )
        )
    return results


def process_push(db: Client, user_id: int, body: SyncPushIn, now: datetime) -> dict[str, Any]:
    return {
        "server_time": now.isoformat(),
        "progress": _process(db, user_id, now, body.progress, ProgressPush, record_progress),
        "quiz_attempts": _process(db, user_id, now, body.quiz_attempts, QuizAttemptPush, record_quiz_attempt),
        "practice_results": _process(db, user_id, now, body.practice_results, PracticePush, record_practice),
        "progress_snapshot": list_progress(db, user_id),
    }
