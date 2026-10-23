from flask import Blueprint, g, jsonify, request

from ..db import get_db
from ..errors import ApiError
from ..security import auth_required, now_iso
from ..services import progress as prog
from .motifs import motif_public

bp = Blueprint("modules", __name__, url_prefix="/api/modules")

OPTION_KEYS = ("A", "B", "C", "D")


def _module_or_404(db, module_id: int):
    row = db.execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
    if row is None:
        raise ApiError(404, "module_not_found", "Modul tidak ditemukan.")
    return row


def module_public(row) -> dict:
    return {
        "id": row["id"],
        "motif_id": row["motif_id"],
        "title": row["title"],
        "description": row["description"],
        "cover_image": row["cover_image"],
        "video_url": row["video_url"],
        "passing_score": row["passing_score"],
        "order_no": row["order_no"],
    }


# --- daftar & detail ---------------------------------------------------------
@bp.get("")
@auth_required
def list_modules():
    db = get_db()
    rows = db.execute(
        """SELECT m.*, p.status, p.progress_percent, p.history_done, p.character_done,
                  p.gallery_done, p.quiz_done, p.practice_done, p.completed_at, p.last_accessed_at
             FROM modules m
             LEFT JOIN user_module_progress p ON p.module_id = m.id AND p.user_id = ?
            ORDER BY m.order_no""",
        (g.user["id"],),
    ).fetchall()
    scores = prog.best_scores(db, g.user["id"])
    out = []
    for r in rows:
        item = module_public(r)
        if r["status"] is None:
            item.update(prog.empty_progress())
        else:
            item.update(prog.serialize(r))
        item["quiz_best_score"] = scores.get(r["id"], {}).get("quiz_best_score")
        item["practice_best_score"] = scores.get(r["id"], {}).get("practice_best_score")
        out.append(item)
    return jsonify({"modules": out})


@bp.get("/<int:module_id>")
@auth_required
def get_module(module_id: int):
    db = get_db()
    module = _module_or_404(db, module_id)
    motif = db.execute("SELECT * FROM batik_motifs WHERE id = ?", (module["motif_id"],)).fetchone()

    contents: dict[str, list] = {"sejarah_filosofi": [], "karakteristik": [], "galeri": []}
    for c in db.execute(
        "SELECT pillar, title, body, badge, order_no FROM module_contents WHERE module_id = ? ORDER BY pillar, order_no",
        (module_id,),
    ):
        contents[c["pillar"]].append(
            {"title": c["title"], "body": c["body"], "badge": c["badge"], "order_no": c["order_no"]}
        )

    gallery = [
        {"id": r["id"], "image_url": r["image_url"], "caption": r["caption"], "order_no": r["order_no"]}
        for r in db.execute(
            "SELECT * FROM module_gallery_images WHERE module_id = ? ORDER BY order_no", (module_id,)
        )
    ]
    question_count = db.execute("SELECT COUNT(*) FROM quiz_questions WHERE module_id = ?", (module_id,)).fetchone()[0]

    with db:
        prog.touch(db, g.user["id"], module_id)
    out = module_public(module)
    out.update(
        motif=motif_public(motif),
        contents=contents,
        gallery=gallery,
        quiz_question_count=question_count,
        progress=prog.get_progress(db, g.user["id"], module_id),
    )
    return jsonify({"module": out})


@bp.post("/<int:module_id>/pillars/<pillar>")
@auth_required
def complete_pillar(module_id: int, pillar: str):
    column = prog.PILLAR_COLUMN.get(pillar)
    if column is None:
        raise ApiError(404, "pillar_not_found", f"Pilar harus salah satu dari: {', '.join(prog.PILLAR_COLUMN)}.")
    db = get_db()
    _module_or_404(db, module_id)
    with db:
        progress = prog.mark_done(db, g.user["id"], module_id, column)
    return jsonify({"progress": progress})


# --- kuis teori --------------------------------------------------------------
@bp.get("/<int:module_id>/quiz")
@auth_required
def get_quiz(module_id: int):
    db = get_db()
    module = _module_or_404(db, module_id)
    limit = request.args.get("limit", type=int)
    is_random = str(request.args.get("random", "")).lower() in ("1", "true", "yes")

    if is_random and limit and limit > 0:
        rows = db.execute(
            "SELECT * FROM quiz_questions WHERE module_id = ? ORDER BY RANDOM() LIMIT ?",
            (module_id, limit),
        ).fetchall()
    elif limit and limit > 0:
        rows = db.execute(
            "SELECT * FROM quiz_questions WHERE module_id = ? ORDER BY id LIMIT ?",
            (module_id, limit),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM quiz_questions WHERE module_id = ? ORDER BY id",
            (module_id,),
        ).fetchall()

    questions = [
        {
            "id": q["id"],
            "no": i,
            "question": q["question"],
            "options": {"A": q["option_a"], "B": q["option_b"], "C": q["option_c"], "D": q["option_d"]},
        }
        for i, q in enumerate(rows, start=1)
    ]
    return jsonify({"module_id": module_id, "passing_score": module["passing_score"], "total": len(questions), "questions": questions})


@bp.post("/<int:module_id>/quiz/attempts")
@auth_required
def submit_quiz(module_id: int):
    db = get_db()
    module = _module_or_404(db, module_id)
    body = request.get_json(silent=True)
    answers = body.get("answers") if isinstance(body, dict) else None
    if not isinstance(answers, list) or not answers:
        raise ApiError(400, "invalid_body", "Body harus berisi 'answers' (list tidak kosong).")

    questions = {q["id"]: q for q in db.execute("SELECT * FROM quiz_questions WHERE module_id = ?", (module_id,))}
    if not questions:
        raise ApiError(409, "quiz_empty", "Modul ini belum memiliki soal kuis.")

    chosen: dict[int, str] = {}
    for a in answers:
        qid = a.get("question_id") if isinstance(a, dict) else None
        opt = a.get("selected_option") if isinstance(a, dict) else None
        opt = opt.strip().upper() if isinstance(opt, str) else None
        if not isinstance(qid, int) or isinstance(qid, bool) or qid not in questions:
            raise ApiError(422, "invalid_question", f"question_id {qid!r} bukan soal dari modul ini.")
        if opt not in OPTION_KEYS:
            raise ApiError(422, "invalid_option", "selected_option harus A, B, C, atau D.")
        if qid in chosen:
            raise ApiError(422, "duplicate_answer", f"Soal {qid} dijawab lebih dari sekali.")
        chosen[qid] = opt

    results = []
    correct_count = 0
    for qid, opt in chosen.items():
        q = questions[qid]
        ok = opt == q["correct_option"]
        correct_count += ok
        results.append(
            {
                "question_id": qid,
                "selected_option": opt,
                "correct_option": q["correct_option"],
                "is_correct": ok,
                "explanation": q["explanation"],
            }
        )

    # Dukung penilaian on-device (offline sync) maupun online grading
    custom_total = body.get("total_questions") if isinstance(body, dict) else None
    if isinstance(custom_total, int) and custom_total > 0:
        total = custom_total
    else:
        total = len(questions)

    custom_score = body.get("score") if isinstance(body, dict) else None
    custom_passed = body.get("passed") if isinstance(body, dict) else None
    if isinstance(custom_score, int) and isinstance(custom_passed, bool):
        score = max(0, min(100, custom_score))
        passed = custom_passed
    else:
        score = round(correct_count * 100 / total) if total > 0 else 0
        passed = score >= module["passing_score"]

    custom_time = body.get("attempted_at") if isinstance(body, dict) else None
    now = custom_time if isinstance(custom_time, str) and custom_time else now_iso()

    with db:
        cur = db.execute(
            "INSERT INTO quiz_attempts (user_id, module_id, score, passed, attempted_at) VALUES (?, ?, ?, ?, ?)",
            (g.user["id"], module_id, score, int(passed), now),
        )
        attempt_id = cur.lastrowid
        db.executemany(
            "INSERT INTO quiz_attempt_answers (attempt_id, question_id, selected_option, is_correct) VALUES (?, ?, ?, ?)",
            [(attempt_id, r["question_id"], r["selected_option"], int(r["is_correct"])) for r in results],
        )
        if passed:
            progress = prog.mark_done(db, g.user["id"], module_id, "quiz_done")
        else:
            prog.touch(db, g.user["id"], module_id)
            progress = prog.get_progress(db, g.user["id"], module_id)

    return (
        jsonify(
            {
                "attempt": {
                    "id": attempt_id,
                    "module_id": module_id,
                    "score": score,
                    "passed": passed,
                    "correct_count": correct_count,
                    "total": total,
                    "passing_score": module["passing_score"],
                    "attempted_at": now,
                },
                "results": results,
                "progress": progress,
            }
        ),
        201,
    )


@bp.get("/<int:module_id>/quiz/attempts")
@auth_required
def list_attempts(module_id: int):
    db = get_db()
    _module_or_404(db, module_id)
    rows = db.execute(
        "SELECT id, score, passed, attempted_at FROM quiz_attempts WHERE user_id = ? AND module_id = ? ORDER BY id DESC",
        (g.user["id"], module_id),
    ).fetchall()
    attempts = [{"id": r["id"], "score": r["score"], "passed": bool(r["passed"]), "attempted_at": r["attempted_at"]} for r in rows]
    return jsonify({"attempts": attempts, "best_score": max((a["score"] for a in attempts), default=None)})
