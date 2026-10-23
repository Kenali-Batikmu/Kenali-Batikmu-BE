import re

from flask import Blueprint, current_app, g, jsonify, request, send_from_directory

from ..db import IntegrityError, get_db
from ..errors import ApiError
from ..security import auth_required, hash_password, now_iso
from .auth import _EMAIL_RE, MAX_PASSWORD_LENGTH, user_public
from ..services import uploads

bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@bp.get("")
@auth_required
def get_profile():
    db = get_db()
    uid = g.user["id"]
    total = db.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
    completed = db.execute(
        "SELECT COUNT(*) FROM user_module_progress WHERE user_id = ? AND progress_percent >= 100", (uid,)
    ).fetchone()[0]
    scanned = db.execute("SELECT COUNT(*) FROM scans WHERE user_id = ?", (uid,)).fetchone()[0]
    completed_modules = db.execute(
        """SELECT m.id, m.title, m.motif_id, p.completed_at
             FROM user_module_progress p JOIN modules m ON m.id = p.module_id
            WHERE p.user_id = ? AND p.progress_percent >= 100 ORDER BY m.order_no""",
        (uid,),
    ).fetchall()
    return jsonify(
        {
            "user": user_public(g.user),
            "stats": {
                "completed_modules": completed,
                "total_modules": total,
                "overall_progress_percent": round(completed * 100 / total) if total else 0,
                "scanned_count": scanned,
            },
            "completed_modules": [
                {"id": r["id"], "title": r["title"].replace("\n", " "), "motif_id": r["motif_id"], "completed_at": r["completed_at"]}
                for r in completed_modules
            ],
        }
    )


_PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{5,19}$")


@bp.patch("")
@auth_required
def update_profile():
    """Ubah nama, email, nomor HP, dan/atau kata sandi. Field yang tidak dikirim tidak berubah.

    Nomor HP kosong ("") menghapus nomor. Kata sandi kosong ("") berarti tidak diubah
    (sama seperti perilaku layar profil di app).
    """
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError(400, "invalid_json", "Body harus berupa JSON object.")

    def text(key):
        value = body.get(key)
        return value.strip() if isinstance(value, str) else None

    name, email, phone = text("name"), text("email"), text("phone")
    password = body.get("password") if isinstance(body.get("password"), str) else None
    user = g.user
    changes: dict[str, object] = {}

    if name is not None:
        if not name:
            raise ApiError(422, "validation_error", "Nama lengkap wajib diisi", field="name")
        if len(name) > 100:
            raise ApiError(422, "validation_error", "Nama maksimal 100 karakter", field="name")
        changes["name"] = name
    if email is not None:
        email = email.lower()
        if len(email) > 254 or not _EMAIL_RE.match(email):
            raise ApiError(422, "validation_error", "Format email tidak valid", field="email")
        changes["email"] = email
    if phone is not None:
        if phone and not _PHONE_RE.match(phone):
            raise ApiError(422, "validation_error", "Format nomor HP tidak valid", field="phone")
        changes["phone"] = phone or None
    if password:  # string kosong = tidak diubah
        min_len = current_app.config["MIN_PASSWORD_LENGTH"]
        if len(password.strip()) < min_len:
            raise ApiError(422, "validation_error", f"Kata sandi minimal {min_len} karakter", field="password")
        if len(password) > MAX_PASSWORD_LENGTH:
            raise ApiError(422, "validation_error", f"Kata sandi maksimal {MAX_PASSWORD_LENGTH} karakter", field="password")
        changes["password_hash"] = hash_password(password)

    if changes:
        changes["updated_at"] = now_iso()
        cols = ", ".join(f"{c} = ?" for c in changes)
        db = get_db()
        try:
            with db:
                db.execute(f"UPDATE users SET {cols} WHERE id = ?", (*changes.values(), user["id"]))
        except IntegrityError:
            raise ApiError(409, "email_taken", "Email sudah terdaftar.", field="email")
    fresh = get_db().execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    return jsonify({"user": user_public(fresh)})


# --- Foto Profil (Avatar) -----------------------------------------------------
@bp.post("/avatar")
@auth_required
def upload_avatar():
    """Unggah foto profil pengguna (avatar).
    Jika pengguna sudah memiliki foto avatar sebelumnya di server, foto lama otomatis dihapus.
    """
    data, ext = uploads.read_image_upload("avatar")
    db = get_db()
    user_id = g.user["id"]

    old_row = db.execute("SELECT profile_image_path FROM users WHERE id = ?", (user_id,)).fetchone()
    if old_row and old_row["profile_image_path"]:
        uploads.delete_image(old_row["profile_image_path"])

    image_name = uploads.save_image(data, ext, subfolder="avatars")
    now = now_iso()
    with db:
        db.execute(
            "UPDATE users SET profile_image_path = ?, updated_at = ? WHERE id = ?",
            (image_name, now, user_id),
        )

    fresh = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return jsonify({"user": user_public(fresh)}), 200


@bp.get("/avatar")
@auth_required
def get_avatar():
    """Ambil file foto profil pengguna aktif."""
    user_id = g.user["id"]
    row = get_db().execute("SELECT profile_image_path FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row or not row["profile_image_path"]:
        raise ApiError(404, "avatar_not_found", "Foto profil tidak tersedia.")

    return send_from_directory(current_app.config["UPLOAD_DIR"], row["profile_image_path"])


@bp.delete("/avatar")
@auth_required
def delete_avatar():
    """Hapus foto profil pengguna aktif dari server."""
    user_id = g.user["id"]
    db = get_db()
    row = db.execute("SELECT profile_image_path FROM users WHERE id = ?", (user_id,)).fetchone()
    if row and row["profile_image_path"]:
        uploads.delete_image(row["profile_image_path"])
        now = now_iso()
        with db:
            db.execute(
                "UPDATE users SET profile_image_path = NULL, updated_at = ? WHERE id = ?",
                (now, user_id),
            )

    fresh = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return jsonify({"user": user_public(fresh)}), 200
