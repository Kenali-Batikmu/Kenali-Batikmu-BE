from flask import Blueprint, jsonify

from ..db import get_db
from ..errors import ApiError
from ..security import auth_required

bp = Blueprint("motifs", __name__, url_prefix="/api/motifs")


def motif_public(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "slug": row["slug"],
        "origin_region": row["origin_region"],
        "short_description": row["short_description"],
        "thumbnail_url": row["thumbnail_url"],
        "ml_class_index": row["ml_class_index"],
    }


@bp.get("")
@auth_required
def list_motifs():
    rows = get_db().execute("SELECT * FROM batik_motifs ORDER BY id").fetchall()
    return jsonify({"motifs": [motif_public(r) for r in rows]})


@bp.get("/<int:motif_id>")
@auth_required
def get_motif(motif_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM batik_motifs WHERE id = ?", (motif_id,)).fetchone()
    if row is None:
        raise ApiError(404, "motif_not_found", "Motif tidak ditemukan.")
    modules = db.execute(
        "SELECT id, title, order_no FROM modules WHERE motif_id = ? ORDER BY order_no", (motif_id,)
    ).fetchall()
    out = motif_public(row)
    out["modules"] = [{"id": m["id"], "title": m["title"], "order_no": m["order_no"]} for m in modules]
    return jsonify({"motif": out})
