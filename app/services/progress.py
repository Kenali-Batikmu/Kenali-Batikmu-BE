from ..security import now_iso

PILLAR_COLUMN = {
    "history": "history_done",
    "character": "character_done",
    "gallery": "gallery_done",
}
COMPONENTS = ("history_done", "character_done", "gallery_done", "quiz_done", "practice_done")
PROGRESS_FIELDS = ("status", "progress_percent", *COMPONENTS, "completed_at", "last_accessed_at")


def _ensure_row(db, user_id: int, module_id: int, now: str) -> None:
    db.execute(
        "INSERT INTO user_module_progress (user_id, module_id, last_accessed_at) VALUES (?, ?, ?) ON CONFLICT (user_id, module_id) DO NOTHING",
        (user_id, module_id, now),
    )


def best_scores(db, user_id: int, module_id: int | None = None) -> dict[int, dict]:
    """Skor terbaik per modul: kuis teori (0-100) dan kuis praktik (fit_score x 100).

    Dipakai app untuk menampilkan nilai, bukan angka bawaan. Modul yang belum pernah
    dikerjakan tidak ada di hasil.
    """
    extra, params = ("", [user_id]) if module_id is None else (" AND module_id = ?", [user_id, module_id])
    out: dict[int, dict] = {}
    for r in db.execute(
        f"SELECT module_id, MAX(score) AS s FROM quiz_attempts WHERE user_id = ?{extra} GROUP BY module_id", params
    ):
        out.setdefault(r["module_id"], {})["quiz_best_score"] = r["s"]
    for r in db.execute(
        f"""SELECT module_id, MAX(fit_score) AS s FROM scans
             WHERE user_id = ? AND scan_type = 'kuismu'{extra} GROUP BY module_id""",
        params,
    ):
        if r["s"] is not None:
            out.setdefault(r["module_id"], {})["practice_best_score"] = round(r["s"] * 100)
    return out


def _with_scores(progress: dict, scores: dict | None) -> dict:
    progress["quiz_best_score"] = (scores or {}).get("quiz_best_score")
    progress["practice_best_score"] = (scores or {}).get("practice_best_score")
    return progress


def get_progress(db, user_id: int, module_id: int) -> dict:
    row = db.execute(
        "SELECT * FROM user_module_progress WHERE user_id = ? AND module_id = ?", (user_id, module_id)
    ).fetchone()
    scores = best_scores(db, user_id, module_id).get(module_id)
    if row is None:
        return _with_scores(empty_progress(), scores)
    return _with_scores(serialize(row), scores)


def empty_progress() -> dict:
    out = {"status": "not_started", "progress_percent": 0, "completed_at": None, "last_accessed_at": None}
    out.update({c: False for c in COMPONENTS})
    return out


def serialize(row) -> dict:
    out = {k: row[k] for k in PROGRESS_FIELDS}
    for c in COMPONENTS:
        out[c] = bool(out[c])
    return out


def touch(db, user_id: int, module_id: int) -> None:
    now = now_iso()
    _ensure_row(db, user_id, module_id, now)
    db.execute(
        "UPDATE user_module_progress SET last_accessed_at = ? WHERE user_id = ? AND module_id = ?",
        (now, user_id, module_id),
    )


def mark_done(db, user_id: int, module_id: int, column: str) -> dict:
    if column not in COMPONENTS:
        raise ValueError(f"kolom progres tidak dikenal: {column}")
    now = now_iso()
    _ensure_row(db, user_id, module_id, now)
    db.execute(
        f"UPDATE user_module_progress SET {column} = 1 WHERE user_id = ? AND module_id = ?",
        (user_id, module_id),
    )
    row = db.execute(
        "SELECT * FROM user_module_progress WHERE user_id = ? AND module_id = ?", (user_id, module_id)
    ).fetchone()

    done = sum(1 for c in COMPONENTS if row[c])
    percent = done * 20
    status = "completed" if percent >= 100 else ("in_progress" if percent > 0 else "not_started")
    completed_at = row["completed_at"] or (now if status == "completed" else None)
    db.execute(
        """UPDATE user_module_progress
              SET progress_percent = ?, status = ?, completed_at = ?, last_accessed_at = ?
            WHERE user_id = ? AND module_id = ?""",
        (percent, status, completed_at, now, user_id, module_id),
    )
    return get_progress(db, user_id, module_id)
