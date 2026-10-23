import math
import time

from flask import Blueprint, current_app, g, jsonify, request, send_from_directory

from ..db import get_db
from ..errors import ApiError
from ..security import auth_required, now_iso
from ..services import progress as prog
from ..services import uploads
from ..services.ml import get_classifier
from .modules import _module_or_404

bp = Blueprint("scans", __name__, url_prefix="/api")


def rating(score: float) -> str:
    cfg = current_app.config
    if score >= cfg["SCORE_VERY_SIMILAR"]:
        return "sangat_mirip"
    if score >= cfg["SCORE_FAIRLY_SIMILAR"]:
        return "cukup_mirip"
    return "perlu_dilatih"


def _infer(db, image_bytes: bytes) -> tuple[list[dict], int]:
    motifs = db.execute("SELECT * FROM batik_motifs ORDER BY ml_class_index").fetchall()
    n = len(motifs)
    if n == 0:
        raise ApiError(503, "no_motifs", "Data motif belum tersedia.")
    if [m["ml_class_index"] for m in motifs] != list(range(n)):
        raise ApiError(500, "model_mismatch", "ml_class_index motif harus berurutan 0..N-1.")

    t0 = time.perf_counter()
    probs = get_classifier().predict(image_bytes, n)
    elapsed_ms = max(1, int((time.perf_counter() - t0) * 1000))

    if len(probs) != n or any((not isinstance(p, (int, float))) or not math.isfinite(p) for p in probs):
        raise ApiError(500, "model_mismatch", "Keluaran model tidak sesuai jumlah kelas motif.")
    probs = [min(1.0, max(0.0, float(p))) for p in probs]

    ranking = [
        {
            "motif_id": m["id"],
            "name": m["name"],
            "slug": m["slug"],
            "origin_region": m["origin_region"],
            "probability": round(p, 6),
            "percent": round(p * 100),
        }
        for m, p in zip(motifs, probs)
    ]
    ranking.sort(key=lambda r: -r["probability"])
    for i, r in enumerate(ranking, start=1):
        r["rank"] = i
    return ranking, elapsed_ms


def _store_scan(db, *, scan_type, module_id, image_name, ranking, confidence, fit_score, passed, elapsed_ms) -> tuple[int, str]:
    now = now_iso()
    cur = db.execute(
        """INSERT INTO scans (user_id, scan_type, module_id, image_path, top_motif_id, confidence,
                              fit_score, passed, inference_time_ms, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (g.user["id"], scan_type, module_id, image_name, ranking[0]["motif_id"], confidence,
         fit_score, None if passed is None else int(passed), elapsed_ms, now),
    )
    db.executemany(
        "INSERT INTO scan_probabilities (scan_id, motif_id, probability) VALUES (?, ?, ?)",
        [(cur.lastrowid, r["motif_id"], r["probability"]) for r in ranking],
    )
    return cur.lastrowid, now


# --- Scan Batik Universal ----------------------------------------------------
@bp.post("/scans/universal")
@auth_required
def scan_universal():
    data, ext = uploads.read_image_upload("image")
    db = get_db()
    ranking, elapsed_ms = _infer(db, data)
    top = ranking[0]

    image_name = uploads.save_image(data, ext)
    try:
        with db:
            scan_id, created_at = _store_scan(
                db, scan_type="universal", module_id=None, image_name=image_name, ranking=ranking,
                confidence=top["probability"], fit_score=None, passed=None, elapsed_ms=elapsed_ms,
            )
    except Exception:
        uploads.delete_image(image_name)
        raise

    suggested = db.execute(
        "SELECT id, title FROM modules WHERE motif_id = ? ORDER BY order_no LIMIT 1", (top["motif_id"],)
    ).fetchone()
    motif = db.execute("SELECT short_description FROM batik_motifs WHERE id = ?", (top["motif_id"],)).fetchone()
    return (
        jsonify(
            {
                "scan": {
                    "id": scan_id, "scan_type": "universal", "confidence": top["probability"],
                    "inference_time_ms": elapsed_ms, "created_at": created_at,
                },
                "top_match": {
                    **top,
                    "short_description": motif["short_description"],
                    "suggested_module": {"id": suggested["id"], "title": suggested["title"]} if suggested else None,
                },
                "top5": ranking[:5],
            }
        ),
        201,
    )


# --- Kuis Praktik (scan pada modul) -------------------------------------------
@bp.post("/modules/<int:module_id>/practice")
@auth_required
def submit_practice(module_id: int):
    db = get_db()
    module = _module_or_404(db, module_id)
    data, ext = uploads.read_image_upload("image")
    ranking, elapsed_ms = _infer(db, data)

    target = next(r for r in ranking if r["motif_id"] == module["motif_id"])
    fit = target["probability"]
    passed = fit >= module["passing_score"] / 100
    top = ranking[0]

    # Kebijakan retensi kuis praktik: Hapus foto lama milik user di modul ini (maks 1 foto per modul)
    old_scans = db.execute(
        "SELECT id, image_path FROM scans WHERE user_id = ? AND module_id = ? AND scan_type = 'kuismu' AND image_path IS NOT NULL",
        (g.user["id"], module_id),
    ).fetchall()
    for os_row in old_scans:
        if os_row["image_path"]:
            uploads.delete_image(os_row["image_path"])

    image_name = uploads.save_image(data, ext, subfolder="practices")
    try:
        with db:
            # Kosongkan image_path scan kuis lama di modul ini agar tidak mengarah ke file yang sudah dihapus
            if old_scans:
                db.execute(
                    "UPDATE scans SET image_path = NULL WHERE user_id = ? AND module_id = ? AND scan_type = 'kuismu'",
                    (g.user["id"], module_id),
                )
            scan_id, created_at = _store_scan(
                db, scan_type="kuismu", module_id=module_id, image_name=image_name, ranking=ranking,
                confidence=top["probability"], fit_score=fit, passed=passed, elapsed_ms=elapsed_ms,
            )
            if passed:
                progress = prog.mark_done(db, g.user["id"], module_id, "practice_done")
            else:
                prog.touch(db, g.user["id"], module_id)
                progress = prog.get_progress(db, g.user["id"], module_id)
    except Exception:
        uploads.delete_image(image_name)
        raise

    return (
        jsonify(
            {
                "scan": {
                    "id": scan_id, "scan_type": "kuismu", "module_id": module_id, "fit_score": fit,
                    "passed": passed, "rating": rating(fit), "passing_score": module["passing_score"],
                    "inference_time_ms": elapsed_ms, "created_at": created_at,
                },
                "target_motif": target,
                "top_match": top,
                "ranking": ranking,
                "progress": progress,
            }
        ),
        201,
    )


# --- Riwayat -----------------------------------------------------------------
def _int_arg(name: str, default: int, lo: int, hi: int) -> int:
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        return min(hi, max(lo, int(raw)))
    except ValueError:
        raise ApiError(422, "validation_error", f"Parameter '{name}' harus berupa bilangan bulat.", field=name)


@bp.get("/scans")
@auth_required
def list_scans():
    scan_type = request.args.get("type")
    if scan_type not in (None, "universal", "kuismu"):
        raise ApiError(422, "validation_error", "type harus 'universal' atau 'kuismu'.", field="type")
    limit = _int_arg("limit", 50, 1, 100)
    offset = _int_arg("offset", 0, 0, 10**9)
    threshold = current_app.config["UNIVERSAL_PASS_THRESHOLD"]

    where, params = "s.user_id = ?", [g.user["id"]]
    if scan_type:
        where += " AND s.scan_type = ?"
        params.append(scan_type)
    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM scans s WHERE {where}", params).fetchone()[0]
    rows = db.execute(
        f"""SELECT s.*, bm.name AS motif_name, md.title AS module_title
              FROM scans s
              LEFT JOIN batik_motifs bm ON bm.id = s.top_motif_id
              LEFT JOIN modules md      ON md.id = s.module_id
             WHERE {where} ORDER BY s.id DESC LIMIT ? OFFSET ?""",
        [*params, limit, offset],
    ).fetchall()

    scans = []
    for r in rows:
        score = r["fit_score"] if r["scan_type"] == "kuismu" else r["confidence"]
        passed = bool(r["passed"]) if r["passed"] is not None else (r["confidence"] or 0) >= threshold
        scans.append(
            {
                "id": r["id"], "scan_type": r["scan_type"], "motif_name": r["motif_name"],
                "module_id": r["module_id"],
                "module_title": r["module_title"].replace("\n", " ") if r["module_title"] else None,
                "score": score, "passed": passed, "created_at": r["created_at"],
            }
        )
    return jsonify({"total": total, "limit": limit, "offset": offset, "scans": scans})


def _own_scan_or_404(db, scan_id: int):
    row = db.execute("SELECT * FROM scans WHERE id = ? AND user_id = ?", (scan_id, g.user["id"])).fetchone()
    if row is None:
        raise ApiError(404, "scan_not_found", "Data scan tidak ditemukan.")
    return row


@bp.get("/scans/<int:scan_id>")
@auth_required
def get_scan(scan_id: int):
    db = get_db()
    s = _own_scan_or_404(db, scan_id)
    probs = db.execute(
        """SELECT sp.motif_id, bm.name, bm.origin_region, sp.probability
             FROM scan_probabilities sp JOIN batik_motifs bm ON bm.id = sp.motif_id
            WHERE sp.scan_id = ? ORDER BY sp.probability DESC, bm.ml_class_index""",
        (scan_id,),
    ).fetchall()
    ranking = [
        {"rank": i, "motif_id": p["motif_id"], "name": p["name"], "origin_region": p["origin_region"],
         "probability": p["probability"], "percent": round(p["probability"] * 100)}
        for i, p in enumerate(probs, start=1)
    ]
    return jsonify(
        {
            "scan": {
                "id": s["id"], "scan_type": s["scan_type"], "module_id": s["module_id"],
                "top_motif_id": s["top_motif_id"], "confidence": s["confidence"], "fit_score": s["fit_score"],
                "passed": None if s["passed"] is None else bool(s["passed"]),
                "rating": rating(s["fit_score"]) if s["fit_score"] is not None else None,
                "inference_time_ms": s["inference_time_ms"], "has_image": bool(s["image_path"]),
                "created_at": s["created_at"],
            },
            "ranking": ranking,
        }
    )


@bp.get("/scans/<int:scan_id>/image")
@auth_required
def get_scan_image(scan_id: int):
    s = _own_scan_or_404(get_db(), scan_id)
    if not s["image_path"]:
        raise ApiError(404, "image_not_found", "Gambar tidak tersedia.")
    return send_from_directory(current_app.config["UPLOAD_DIR"], s["image_path"])
