"""Uji asap ujung-ke-ujung terhadap server yang SEDANG berjalan (hanya pustaka standar).

    python scripts/smoke_test.py http://127.0.0.1:8000

Syarat: db/schema.sql dan db/seed_reference_data.sql sudah dijalankan di Supabase.
Akun uji dibuat dengan email acak @example.test; hapus manual dari tabel `users` sesudahnya.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
import uuid

ROOT = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
BASE = ROOT + "/api/v1"


def call(method: str, path: str, body=None, token: str | None = None, expect=(200,), root: bool = False):
    url = (ROOT if root else BASE) + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as err:
        status, raw = err.code, err.read()
    payload = json.loads(raw) if raw else None
    ok = status in expect
    print(("OK    " if ok else "GAGAL "), f"{method:6} {path} -> {status}")
    if not ok:
        print("       ", payload)
        sys.exit(1)
    return payload


def check(condition: bool, message: str) -> None:
    print(("OK    " if condition else "GAGAL "), message)
    if not condition:
        sys.exit(1)


call("GET", "/health/db", root=True)

email = f"smoke-{uuid.uuid4().hex[:10]}@example.test"
password = "Batikmu123#"
reg = call("POST", "/auth/register", {"name": "Smoke Test", "email": email, "password": password}, expect=(201,))
call("POST", "/auth/login", {"email": email, "password": "salah-total"}, expect=(401,))
auth = call("POST", "/auth/login", {"email": email, "password": password})
token = auth["access_token"]
check(auth["user"]["id"] == reg["user"]["id"], "login mengembalikan pengguna yang sama")
call("GET", "/me", token=token)
call("GET", "/me", expect=(401,))

batch = {
    "progress": [{"module_id": 1, "history_done": True, "character_done": True, "gallery_done": True}],
    "quiz_attempts": [{"module_id": 1, "score": 80, "total_questions": 10, "client_ref": "smoke-q1"}],
    "practice_results": [{"module_id": 1, "confidence": 0.9}],
}
out = call("POST", "/sync/push", batch, token=token)
statuses = [r["status"] for k in ("progress", "quiz_attempts", "practice_results") for r in out[k]]
check(statuses == ["accepted"] * 3, f"push diterima semua: {statuses}")
snap = {r["module_id"]: r for r in out["progress_snapshot"]}
check(snap[1]["progress_percent"] == 100 and snap[1]["status"] == "completed", "modul 1 selesai 100% (3 bacaan + kuis + praktikum)")

again = call("POST", "/sync/push", batch, token=token)
check(again["quiz_attempts"][0]["status"] == "duplicate", "kirim ulang client_ref yang sama = duplicate")

pulled = call("GET", "/sync/pull", token=token)
check(len(pulled["progress"]) == 1 and pulled["progress"][0]["quiz_score"] == 80, "pull: progres & skor kuis tersedia")
check(len(pulled["quiz_attempts"]) == 1, "pull: tepat 1 riwayat kuis (tidak ganda)")
check(len(pulled["practice_results"]) == 1 and pulled["practice_results"][0]["passed"] is True, "pull: hasil praktikum lulus")
call("GET", "/progress", token=token)
call("GET", "/quiz/attempts", token=token)
call("GET", "/practice", token=token)

new_since = call("GET", "/sync/pull?since=" + pulled["server_time"].replace("+", "%2B"), token=token)
check(new_since["progress"] == [] and new_since["quiz_attempts"] == [], "pull inkremental setelah server_time = kosong")

mixed = call("POST", "/sync/push", {"quiz_attempts": [
    {"module_id": 1, "score": 150, "client_ref": "smoke-bad"},   # cacat: skor > 100
    {"module_id": 1, "score": 60, "client_ref": "smoke-q2"},
]}, token=token)
check([r["status"] for r in mixed["quiz_attempts"]] == ["rejected", "accepted"], "item cacat ditolak sendiri, item valid tetap tersimpan (HTTP 200)")

ref = call("POST", "/auth/refresh", {"refresh_token": auth["refresh_token"]})
call("GET", "/me", token=ref["access_token"])
call("POST", "/auth/logout", {"refresh_token": auth["refresh_token"]}, expect=(204,))
call("POST", "/auth/refresh", {"refresh_token": auth["refresh_token"]}, expect=(401,))

print(f"\nSemua pemeriksaan lulus. Hapus akun uji dari tabel users: {email}")
