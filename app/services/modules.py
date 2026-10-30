"""Cache kecil data referensi modul (id, motif_id, passing_score).

Backend tidak menyimpan/menyajikan isi modul. Tabel `modules` hanya dipakai untuk
memvalidasi module_id dan membaca KKM (passing_score) yang berlaku.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from supabase import Client

_TTL_SECONDS = 300
_MISS_REFRESH_SECONDS = 30
_lock = threading.Lock()
_cache: dict[str, Any] = {"at": 0.0, "data": {}}


def _load(db: Client) -> dict[int, dict[str, Any]]:
    rows = db.table("modules").select("id,motif_id,passing_score").execute().data or []
    data = {int(r["id"]): r for r in rows}
    with _lock:
        _cache["at"] = time.monotonic()
        _cache["data"] = data
    return data


def get_module(db: Client, module_id: int) -> dict[str, Any] | None:
    now = time.monotonic()
    with _lock:
        age = now - _cache["at"]
        data = _cache["data"]
    reloaded = False
    if not data or age > _TTL_SECONDS:
        data = _load(db)
        reloaded = True
    module = data.get(module_id)
    if module is None and not reloaded and age > _MISS_REFRESH_SECONDS:
        module = _load(db).get(module_id)  # mungkin modul baru ditambahkan
    return module
