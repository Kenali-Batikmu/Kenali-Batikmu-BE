"""CLI pengelolaan database (SQLite).

    python manage.py init-db          # buat tabel (idempotent)
    python manage.py seed             # isi motif, modul, materi, soal (jika kosong)
    python manage.py seed-demo        # akun demo pengembangan (sekar@batikmu.id, dst.)
    python manage.py reset --yes      # HAPUS database lalu buat ulang + seed
"""
import argparse
import os
import sys

from app.config import Config
from app.db import connect, init_db, seed_db
from app.seed import seed_demo_users


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")
    sub.add_parser("seed")
    sub.add_parser("seed-demo")
    p_reset = sub.add_parser("reset")
    p_reset.add_argument("--yes", action="store_true", help="konfirmasi menghapus database")
    args = parser.parse_args()

    target = Config.DATABASE

    if args.cmd == "reset":
        if not args.yes:
            print(f"Ini akan MENGHAPUS database {target}. Jalankan ulang dengan --yes untuk melanjutkan.")
            return 1
        for suffix in ("", "-wal", "-shm"):
            path = target + suffix
            if os.path.exists(path):
                os.remove(path)

    init_db(target)
    if args.cmd in ("seed", "reset"):
        seed_db(target)
        print("Seed data: selesai")

    if args.cmd == "seed-demo":
        conn = connect(target)
        try:
            print(f"Akun demo dibuat: {seed_demo_users(conn)}")
        finally:
            conn.close()

    print(f"Database siap: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
