"""Akun demo untuk pengembangan.

Data referensi (motif, modul, materi, soal) ada di seed.sqlite.sql dan dimuat oleh
db.seed_db. Berkas ini HANYA membuat akun demo yang dulu tertanam di app mobile
supaya login lama tetap bisa dipakai saat uji coba. Password-nya publik, jadi jangan
aktifkan (SEED_DEMO_USERS=1) di produksi.
"""
from typing import Any

from .security import hash_password, now_iso

DEMO_USERS = [
    # (nama, email, password, telepon)
    ("Sekar Ayu Kinanti", "sekar@batikmu.id", "Batikmu123#", "081234567890"),
    ("Kenali Batikmu", "kenalibatikmu@gmail.com", "kenalibatikmupbl", None),
]
DEMO_EMAIL, DEMO_PASSWORD = DEMO_USERS[0][1], DEMO_USERS[0][2]


def seed_demo_users(db: Any) -> int:
    """Buat akun demo yang belum ada. Mengembalikan jumlah akun yang dibuat."""
    created = 0
    now = now_iso()
    with db:
        for name, email, password, phone in DEMO_USERS:
            if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
                continue
            db.execute(
                "INSERT INTO users (name, email, phone, password_hash, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                (name, email, phone, hash_password(password), now, now),
            )
            created += 1
    return created
