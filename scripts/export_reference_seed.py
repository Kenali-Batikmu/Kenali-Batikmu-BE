"""Ekspor data referensi (batik_motifs & modules) dari database SQLite bawaan aplikasi
menjadi SQL untuk Supabase.

Pemakaian:
    python scripts/export_reference_seed.py path/ke/kenali_batikmu.db > db/seed_reference_data.sql

Hanya id, judul, KKM, dsb. Isi modul (module_contents), galeri, dan soal kuis TIDAK diekspor
karena tetap dibaca dari database lokal di aplikasi.
"""

from __future__ import annotations

import sqlite3
import sys


def lit(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def dump(conn: sqlite3.Connection, table: str, columns: list[str], order: str) -> str:
    rows = conn.execute(f"select {', '.join(columns)} from {table} order by {order}").fetchall()
    values = ",\n".join("  (" + ", ".join(lit(v) for v in row) + ")" for row in rows)
    updates = ",\n".join(f"  {c} = excluded.{c}" for c in columns if c != "id")
    return (
        f"insert into public.{table} ({', '.join(columns)}) values\n{values}\n"
        f"on conflict (id) do update set\n{updates};\n"
    )


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    conn = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
    print("-- Dibuat oleh scripts/export_reference_seed.py dari assets/database/kenali_batikmu.db")
    print("-- Jalankan SETELAH db/schema.sql. Aman dijalankan ulang.\n")
    print(dump(conn, "batik_motifs",
               ["id", "name", "slug", "origin_region", "short_description", "thumbnail_url", "ml_class_index"], "id"))
    print(dump(conn, "modules",
               ["id", "motif_id", "title", "description", "cover_image", "video_url", "passing_score", "order_no"], "id"))


if __name__ == "__main__":
    main()
