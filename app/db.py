import logging
import sqlite3
from pathlib import Path

from flask import current_app, g

log = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).with_name("schema.sqlite.sql")
SEED_PATH = Path(__file__).with_name("seed.sqlite.sql")

# Naikkan angka ini setiap skema berubah, lalu tambahkan langkahnya di _MIGRATIONS.
SCHEMA_VERSION = 2

IntegrityError = sqlite3.IntegrityError


def connect(target: str = None):
    if target is None:
        target = current_app.config["DATABASE"]
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


# --- migrasi -----------------------------------------------------------------
def _columns(conn, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _add_column(conn, table: str, ddl: str) -> None:
    name = ddl.split()[0]
    if name not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _migrate_to_2(conn) -> None:
    """v1 -> v2: kolom yang dibutuhkan app mobile (nomor HP, video, badge materi).

    Tabel password_resets dibuat oleh schema.sqlite.sql (CREATE TABLE IF NOT EXISTS).
    image_url di module_gallery_images yang dulu NOT NULL tidak bisa diubah lewat ALTER;
    app selalu mengirim nilai, jadi cukup dibiarkan pada database lama.
    """
    _add_column(conn, "users", "phone TEXT")
    _add_column(conn, "modules", "video_url TEXT")
    _add_column(conn, "module_contents", "badge TEXT")


_MIGRATIONS = {2: _migrate_to_2}


def init_db(target: str = None) -> None:
    """Buat tabel (idempotent) dan jalankan migrasi untuk database lama."""
    if target is None:
        target = current_app.config["DATABASE"]
    conn = sqlite3.connect(target)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        had_tables = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone() is not None
        current = conn.execute("PRAGMA user_version").fetchone()[0]
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        if had_tables and current < SCHEMA_VERSION:
            for version in range(current + 1, SCHEMA_VERSION + 1):
                step = _MIGRATIONS.get(version)
                if step:
                    log.info("Migrasi database ke versi %d", version)
                    step(conn)
            log.warning(
                "Database lama dimigrasi ke skema v%d. Struktur sudah diperbarui, tetapi "
                "DATA (materi, nama motif, cover) tetap versi lama. Untuk memuat data terbaru: "
                "python manage.py reset --yes",
                SCHEMA_VERSION,
            )
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
    finally:
        conn.close()


def seed_db(target: str = None) -> None:
    if target is None:
        target = current_app.config["DATABASE"]
    if not SEED_PATH.exists():
        return
    conn = sqlite3.connect(target)
    try:
        count = conn.execute("SELECT COUNT(*) FROM batik_motifs").fetchone()[0]
        if count > 0:
            return
        conn.executescript(SEED_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
