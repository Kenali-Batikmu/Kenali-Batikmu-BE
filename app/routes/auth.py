import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from flask import Blueprint, current_app, g, jsonify, request

from ..db import IntegrityError, get_db
from ..errors import ApiError
from ..services import mailer
from ..security import (
    auth_required,
    create_token,
    hash_password,
    iso,
    now_iso,
    parse_iso,
    utcnow,
    verify_dummy,
    verify_password,
)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_PASSWORD_LENGTH = 128  # batas atas agar scrypt tidak dipakai untuk DoS


def user_public(row) -> dict:
    has_avatar = "profile_image_path" in row.keys() if hasattr(row, "keys") else False
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "profile_image_path": row["profile_image_path"] if has_avatar else None,
        "created_at": row["created_at"],
    }


def _json_body() -> dict:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError(400, "invalid_json", "Body harus berupa JSON object.")
    return body


def _str_field(body: dict, key: str) -> str:
    value = body.get(key)
    return value if isinstance(value, str) else ""


@bp.post("/register")
def register():
    body = _json_body()
    name = _str_field(body, "name").strip()
    email = _str_field(body, "email").strip().lower()
    password = _str_field(body, "password")
    min_len = current_app.config["MIN_PASSWORD_LENGTH"]

    if not name:
        raise ApiError(422, "validation_error", "Nama lengkap wajib diisi", field="name")
    if len(name) > 100:
        raise ApiError(422, "validation_error", "Nama maksimal 100 karakter", field="name")
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise ApiError(422, "validation_error", "Format email tidak valid", field="email")
    if len(password.strip()) < min_len:
        raise ApiError(422, "validation_error", f"Kata sandi minimal {min_len} karakter", field="password")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ApiError(422, "validation_error", f"Kata sandi maksimal {MAX_PASSWORD_LENGTH} karakter", field="password")

    db = get_db()
    now = now_iso()
    try:
        with db:
            cur = db.execute(
                "INSERT INTO users (name, email, password_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (name, email, hash_password(password), now, now),
            )
    except IntegrityError:
        raise ApiError(409, "email_taken", "Email sudah terdaftar.", field="email")

    user = db.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    token, expires_in = create_token(user["id"])
    return jsonify({"user": user_public(user), "token": token, "token_type": "Bearer", "expires_in": expires_in}), 201


@bp.post("/login")
def login():
    body = _json_body()
    email = _str_field(body, "email").strip().lower()
    password = _str_field(body, "password")
    remember = body.get("remember_me", True) is True
    cfg = current_app.config

    if not email or "@" not in email:
        raise ApiError(422, "validation_error", "Format email tidak valid", field="email")
    if len(password.strip()) < cfg["MIN_PASSWORD_LENGTH"]:
        raise ApiError(422, "validation_error", f"Kata sandi minimal {cfg['MIN_PASSWORD_LENGTH']} karakter", field="password")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ApiError(401, "invalid_credentials", "Email atau kata sandi salah")

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user is None:
        verify_dummy(password)  # samakan waktu respons; jangan bocorkan apakah email terdaftar
        raise ApiError(401, "invalid_credentials", "Email atau kata sandi salah")

    now = utcnow()
    if user["lockout_until"]:
        until = parse_iso(user["lockout_until"])
        if until > now:
            retry = int((until - now).total_seconds()) + 1
            raise ApiError(423, "account_locked", "Terlalu banyak percobaan gagal. Coba lagi nanti.", retry_after_seconds=retry)

    if not verify_password(password, user["password_hash"]):
        failed = user["failed_attempts"] + 1
        locked = failed >= cfg["MAX_FAILED_ATTEMPTS"]
        with db:
            db.execute(
                "UPDATE users SET failed_attempts = ?, lockout_until = ? WHERE id = ?",
                (0 if locked else failed, iso(now + timedelta(minutes=cfg["LOCKOUT_MINUTES"])) if locked else None, user["id"]),
            )
        if locked:
            raise ApiError(
                423, "account_locked", "Terlalu banyak percobaan gagal. Coba lagi nanti.",
                retry_after_seconds=cfg["LOCKOUT_MINUTES"] * 60,
            )
        raise ApiError(401, "invalid_credentials", "Email atau kata sandi salah")

    with db:
        db.execute("UPDATE users SET failed_attempts = 0, lockout_until = NULL WHERE id = ?", (user["id"],))
    token, expires_in = create_token(user["id"], remember=remember)
    return jsonify({"user": user_public(user), "token": token, "token_type": "Bearer", "expires_in": expires_in})


@bp.get("/me")
@auth_required
def me():
    return jsonify({"user": user_public(g.user)})


# --- lupa kata sandi (OTP) ----------------------------------------------------
def _hmac(value: str) -> str:
    key = current_app.config["SECRET_KEY"].encode("utf-8")
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()


def _active_reset(db, user_id: int):
    """Permintaan reset terbaru yang belum dipakai."""
    return db.execute(
        "SELECT * FROM password_resets WHERE user_id = ? AND used_at IS NULL ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()


def _user_by_email(db, email: str):
    return db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def _check_new_password(password: str, field: str = "password") -> None:
    min_len = current_app.config["MIN_PASSWORD_LENGTH"]
    if len(password.strip()) < min_len:
        raise ApiError(422, "validation_error", f"Kata sandi minimal {min_len} karakter", field=field)
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ApiError(422, "validation_error", f"Kata sandi maksimal {MAX_PASSWORD_LENGTH} karakter", field=field)


@bp.post("/forgot-password")
def forgot_password():
    """Buat OTP 4 digit dan kirim ke email. Tanpa SMTP: mode demo (butuh ALLOW_DEMO_OTP=1)."""
    body = _json_body()
    email = _str_field(body, "email").strip().lower()
    cfg = current_app.config
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise ApiError(422, "validation_error", "Format email tidak valid", field="email")

    db = get_db()
    user = _user_by_email(db, email)
    if user is None:
        raise ApiError(404, "email_not_found", "Email belum terdaftar di Kenali Batikmu", field="email")

    now = utcnow()
    last = _active_reset(db, user["id"])
    if last is not None:
        wait = (parse_iso(last["created_at"]) + timedelta(seconds=cfg["OTP_RESEND_SECONDS"])) - now
        if wait.total_seconds() > 0:
            raise ApiError(
                429, "otp_throttled", "Tunggu sebentar sebelum meminta kode baru.",
                retry_after_seconds=int(wait.total_seconds()) + 1,
            )

    use_smtp = mailer.smtp_configured()
    if not use_smtp and not cfg["ALLOW_DEMO_OTP"]:
        raise ApiError(503, "email_not_configured", "Pengiriman email belum dikonfigurasi di server.")

    otp = str(1000 + secrets.randbelow(9000))
    expires = now + timedelta(minutes=cfg["OTP_TTL_MINUTES"])
    with db:
        db.execute("DELETE FROM password_resets WHERE user_id = ?", (user["id"],))
        db.execute(
            "INSERT INTO password_resets (user_id, otp_hash, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (user["id"], _hmac(f"{user['id']}:{otp}"), iso(expires), iso(now)),
        )

    out = {"expires_in": cfg["OTP_TTL_MINUTES"] * 60, "recipient_name": user["name"]}
    if use_smtp:
        try:
            mailer.send_otp_email(user["email"], user["name"], otp)
        except mailer.MailError:
            with db:
                db.execute("DELETE FROM password_resets WHERE user_id = ?", (user["id"],))
            raise ApiError(502, "email_failed", "Gagal mengirim email. Coba lagi nanti.")
        out["delivery"] = "email"
    else:
        out["delivery"] = "demo"
        out["demo_otp"] = otp
    return jsonify(out)


@bp.post("/verify-otp")
def verify_otp():
    body = _json_body()
    email = _str_field(body, "email").strip().lower()
    otp = _str_field(body, "otp").strip()
    cfg = current_app.config
    db = get_db()
    user = _user_by_email(db, email)
    reset = _active_reset(db, user["id"]) if user else None
    if reset is None:
        raise ApiError(422, "otp_not_found", "Sesi pemulihan tidak valid. Silakan minta kode baru.")

    now = utcnow()
    if parse_iso(reset["expires_at"]) <= now:
        raise ApiError(422, "otp_expired", "Kode OTP telah kedaluwarsa. Silakan kirim ulang.")
    if reset["attempts"] >= cfg["OTP_MAX_ATTEMPTS"]:
        raise ApiError(429, "otp_locked", "Terlalu banyak percobaan. Silakan minta kode baru.")

    if not hmac.compare_digest(_hmac(f"{user['id']}:{otp}"), reset["otp_hash"]):
        with db:
            db.execute("UPDATE password_resets SET attempts = attempts + 1 WHERE id = ?", (reset["id"],))
        left = max(0, cfg["OTP_MAX_ATTEMPTS"] - reset["attempts"] - 1)
        raise ApiError(422, "invalid_otp", "Kode verifikasi salah. Periksa kembali kode Anda.", attempts_left=left)

    token = secrets.token_urlsafe(32)
    ttl = timedelta(minutes=cfg["RESET_TOKEN_TTL_MINUTES"])
    with db:
        db.execute(
            "UPDATE password_resets SET verified = 1, reset_token_hash = ?, expires_at = ? WHERE id = ?",
            (_hmac(f"token:{token}"), iso(now + ttl), reset["id"]),
        )
    return jsonify({"reset_token": token, "expires_in": int(ttl.total_seconds())})


@bp.post("/reset-password")
def reset_password():
    body = _json_body()
    email = _str_field(body, "email").strip().lower()
    token = _str_field(body, "reset_token")
    new_password = _str_field(body, "new_password")
    _check_new_password(new_password, field="new_password")

    db = get_db()
    user = _user_by_email(db, email)
    reset = _active_reset(db, user["id"]) if user else None
    ok = (
        reset is not None
        and reset["verified"] == 1
        and reset["reset_token_hash"]
        and hmac.compare_digest(_hmac(f"token:{token}"), reset["reset_token_hash"])
    )
    if not ok:
        raise ApiError(422, "invalid_reset_token", "Sesi pemulihan tidak valid. Silakan ulangi dari awal.")
    if parse_iso(reset["expires_at"]) <= utcnow():
        raise ApiError(422, "otp_expired", "Sesi pemulihan telah berakhir. Silakan ulangi dari awal.")

    with db:
        db.execute(
            "UPDATE users SET password_hash = ?, failed_attempts = 0, lockout_until = NULL, updated_at = ? WHERE id = ?",
            (hash_password(new_password), now_iso(), user["id"]),
        )
        db.execute("DELETE FROM password_resets WHERE user_id = ?", (user["id"],))
    return jsonify({"message": "Kata sandi berhasil diperbarui."})
