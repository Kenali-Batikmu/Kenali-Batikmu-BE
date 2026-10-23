import os
import uuid
from pathlib import Path

from flask import current_app, request

from ..errors import ApiError


def _sniff_ext(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def read_image_upload(field: str = "image") -> tuple[bytes, str]:
    file = request.files.get(field)
    if file is None or not file.filename:
        raise ApiError(400, "image_required", f"Kirim gambar sebagai multipart/form-data dengan field '{field}'.")
    data = file.read()
    if not data:
        raise ApiError(400, "image_empty", "File gambar kosong.")
    ext = _sniff_ext(data)
    if ext is None:
        raise ApiError(415, "unsupported_image", "Format gambar harus JPEG, PNG, atau WebP.")
    return data, ext


def save_image(data: bytes, ext: str) -> str:
    upload_dir = Path(current_app.config["UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    (upload_dir / name).write_bytes(data)
    return name


def delete_image(name: str) -> None:
    try:
        os.remove(Path(current_app.config["UPLOAD_DIR"]) / name)
    except OSError:
        pass
