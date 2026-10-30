from __future__ import annotations

import logging
import time

from supabase import Client

from .domain import detect_image_type

log = logging.getLogger("kenali.storage")


class ImageRejected(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def store_public_image(db: Client, bucket: str, folder: str, stem: str, data: bytes, max_bytes: int) -> str:
    """Simpan 1 gambar per (folder, stem) di Supabase Storage; menimpa yang lama. Kembalikan URL publik."""
    if not data:
        raise ImageRejected(400, "File gambar kosong.")
    if len(data) > max_bytes:
        raise ImageRejected(413, f"Ukuran gambar maksimal {max_bytes // (1024 * 1024)} MB.")
    kind = detect_image_type(data)
    if kind is None:
        raise ImageRejected(415, "Format gambar harus JPEG atau PNG.")
    ext, mime = kind

    api = db.storage.from_(bucket)
    other_ext = "png" if ext == "jpg" else "jpg"
    try:
        api.remove([f"{folder}/{stem}.{other_ext}"])
    except Exception:  # noqa: BLE001
        log.debug("Tidak ada varian lama yang perlu dihapus")

    path = f"{folder}/{stem}.{ext}"
    api.upload(path, data, file_options={"content-type": mime, "upsert": "true"})
    url = str(api.get_public_url(path)).rstrip("?")
    return f"{url}?v={int(time.time())}"  # cache-busting karena path sama saat ditimpa


def remove_images(db: Client, bucket: str, paths: list[str]) -> None:
    try:
        db.storage.from_(bucket).remove(paths)
    except Exception:  # noqa: BLE001
        log.warning("Gagal menghapus file storage", exc_info=True)
