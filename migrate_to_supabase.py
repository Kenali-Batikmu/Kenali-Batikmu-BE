"""
Script Migrasi Data Otomatis: SQLite Lokal -> Supabase PostgreSQL
"""
import os
import sqlite3
import sys

# 1. Muat otomatis variabel DATABASE_URL dari file .env
env_file = os.path.join(os.path.dirname(__file__), ".env")
try:
    from dotenv import load_dotenv
    if os.path.exists(env_file):
        load_dotenv(env_file)
    else:
        load_dotenv()
except ImportError:
    pass

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("Error: Modul psycopg2 belum terpasang. Jalankan: pip install psycopg2-binary")
    sys.exit(1)

# Ambil DATABASE_URL dari environment / .env
SUPABASE_DB_URL = os.environ.get("DATABASE_URL")

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "app", "kenali_batikmu.db")

if not os.path.exists(SQLITE_PATH):
    print(f"Error: File database SQLite tidak ditemukan di {SQLITE_PATH}")
    sys.exit(1)

if not SUPABASE_DB_URL or "[YOUR-PASSWORD]" in SUPABASE_DB_URL or "[YOUR-PROJECT-REF]" in SUPABASE_DB_URL:
    print("PERINGATAN: Variabel DATABASE_URL belum terisi di file .env atau formatnya belum benar.")
    print("Pastikan baris DATABASE_URL di file .env sudah berisi connection string Supabase kamu.")
    sys.exit(1)

print("Menghubungkan ke SQLite lokal dan Supabase PostgreSQL...")
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row
cur_sqlite = sqlite_conn.cursor()

try:
    pg_conn = psycopg2.connect(SUPABASE_DB_URL)
    cur_pg = pg_conn.cursor()
except Exception as e:
    print(f"Gagal terhubung ke Supabase PostgreSQL: {e}")
    sys.exit(1)

tables = [
    "batik_motifs",
    "modules",
    "module_contents",
    "module_gallery_images",
    "quiz_questions",
    "users"
]

print("Memulai proses migrasi data...")
for table in tables:
    cur_sqlite.execute(f"SELECT * FROM {table}")
    rows = cur_sqlite.fetchall()
    if not rows:
        print(f"- Tabel {table}: 0 baris (dilewati)")
        continue

    col_names = [d[0] for d in cur_sqlite.description]
    cols_str = ", ".join(col_names)
    values = [[row[c] for c in col_names] for row in rows]

    insert_query = f"INSERT INTO {table} ({cols_str}) VALUES %s ON CONFLICT DO NOTHING"
    try:
        execute_values(cur_pg, insert_query, values)
        print(f"[OK] Berhasil migrasi {len(rows)} baris ke tabel {table}")
    except Exception as e:
        print(f"[ERR] Gagal migrasi tabel {table}: {e}")
        pg_conn.rollback()
        sys.exit(1)

pg_conn.commit()

# Reset auto-increment sequence di PostgreSQL
print("Menyetel ulang sequence auto-increment...")
for table in tables:
    try:
        cur_pg.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table};")
    except Exception:
        pass

pg_conn.commit()

# Verifikasi jumlah baris di Supabase
print("\n--- STATUS DATA AKTIF DI SUPABASE ---")
for table in tables:
    cur_pg.execute(f"SELECT COUNT(*) FROM {table}")
    cnt = cur_pg.fetchone()[0]
    print(f"Tabel {table:22}: {cnt} baris")

cur_sqlite.close()
cur_pg.close()
sqlite_conn.close()
pg_conn.close()
print("\nSelesai! Seluruh data di Supabase sudah siap digunakan 100%.")
