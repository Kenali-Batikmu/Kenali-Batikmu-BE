"""Menguji alur sinkronisasi dengan database tiruan di memori.

Bila paket `supabase`/`pydantic` belum terpasang, dipakai stub minimal agar tes tetap jalan.
Ini menguji alur kontrol (dedup, merge, item gagal), BUKAN perilaku PostgREST asli.
"""
import logging
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone

try:  # pragma: no cover
    import pydantic  # noqa: F401
except ImportError:  # pragma: no cover
    m = types.ModuleType("pydantic")

    class BaseModel:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

        def model_dump(self):
            return dict(vars(self))

    class ValidationError(Exception):
        def __init__(self, loc, msg):
            super().__init__(msg)
            self._errors = [{"loc": (loc,) if loc else (), "msg": msg}]

        def errors(self):
            return self._errors

    def model_validate(cls, data):
        # Stub: meniru SEBAGIAN aturan skema (module_id >= 1, skor 0..100) agar alur penolakan per
        # item teruji tanpa pydantic. Dengan pydantic asli terpasang, aturan sebenarnya yang dipakai.
        if not isinstance(data, dict):
            raise ValidationError("", "Input should be a valid dictionary")
        mid = data.get("module_id")
        if not isinstance(mid, int) or isinstance(mid, bool) or mid < 1:
            raise ValidationError("module_id", "Input should be a valid integer")
        for key in ("score", "quiz_score", "practice_score", "confidence"):
            v = data.get(key)
            if v is not None and not (0 <= v <= 100):
                raise ValidationError(key, "Input should be less than or equal to 100")
        return cls(**data)

    BaseModel.model_validate = classmethod(model_validate)
    m.ValidationError = ValidationError
    m.BaseModel = BaseModel
    m.Field = lambda *a, **k: k.get("default")
    m.ConfigDict = lambda **k: k
    m.field_validator = lambda *a, **k: (lambda f: f)
    sys.modules["pydantic"] = m

try:  # pragma: no cover
    from supabase import Client  # noqa: F401
except ImportError:  # pragma: no cover
    s = types.ModuleType("supabase")
    s.Client = object
    s.create_client = lambda *a, **k: None
    sys.modules["supabase"] = s

from app.domain import parse_ts  # noqa: E402
from app.schemas import SyncPushIn  # noqa: E402
from app.services import modules as modules_service  # noqa: E402
from app.services.sync import process_push  # noqa: E402

NOW = datetime(2026, 10, 27, 3, 0, 0, tzinfo=timezone.utc)


class Resp:
    def __init__(self, data):
        self.data = data


class Query:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.op, self.payload, self.filters = "select", None, []
        self._order, self._limit, self.conflict, self.ignore = None, None, [], False

    def select(self, cols="*"):
        self.op = "select"
        return self

    def insert(self, row):
        self.op, self.payload = "insert", row
        return self

    def update(self, patch):
        self.op, self.payload = "update", patch
        return self

    def delete(self):
        self.op = "delete"
        return self

    def upsert(self, row, on_conflict="", ignore_duplicates=False):
        self.op, self.payload, self.ignore = "upsert", row, ignore_duplicates
        self.conflict = [c for c in on_conflict.split(",") if c]
        return self

    def eq(self, c, v):
        self.filters.append(("eq", c, v))
        return self

    def gt(self, c, v):
        self.filters.append(("gt", c, v))
        return self

    def lt(self, c, v):
        self.filters.append(("lt", c, v))
        return self

    def is_(self, c, v):
        self.filters.append(("is", c, v))
        return self

    def order(self, c, desc=False):
        self._order = (c, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def _match(self, row):
        for kind, c, v in self.filters:
            val = row.get(c)
            if kind == "eq" and not (val == v or str(val).lower() == str(v).lower()):
                return False
            if kind == "is" and val is not None:
                return False
            if kind == "gt" and not (parse_ts(val) and parse_ts(val) > parse_ts(v)):
                return False
            if kind == "lt" and not (parse_ts(val) and parse_ts(val) < parse_ts(v)):
                return False
        return True

    def execute(self):
        self.db.calls.append((self.table, self.op))
        if self.table in self.db.fail_tables and self.op in ("insert", "update", "upsert"):
            raise RuntimeError("simulasi Supabase down")
        rows = self.db.tables.setdefault(self.table, [])
        if self.op == "select":
            out = [dict(r) for r in rows if self._match(r)]
            if self._order:
                out.sort(key=lambda r: r.get(self._order[0]), reverse=self._order[1])
            return Resp(out[: self._limit] if self._limit else out)
        if self.op == "insert":
            row = dict(self.payload)
            row["id"] = self.db.next_id()
            rows.append(row)
            return Resp([dict(row)])
        if self.op == "update":
            hit = [r for r in rows if self._match(r)]
            for r in hit:
                r.update(self.payload)
            return Resp([dict(r) for r in hit])
        if self.op == "delete":
            self.db.tables[self.table] = [r for r in rows if not self._match(r)]
            return Resp([])
        if self.op == "upsert":
            row = dict(self.payload)
            key = [row.get(c) for c in self.conflict]
            existing = None
            if self.conflict and all(k is not None for k in key):
                existing = next((r for r in rows if [r.get(c) for c in self.conflict] == key), None)
            if existing is not None:
                if self.ignore:
                    return Resp([])
                existing.update(row)
                return Resp([dict(existing)])
            row["id"] = self.db.next_id()
            rows.append(row)
            return Resp([dict(row)])
        raise AssertionError(self.op)


class FakeDB:
    def __init__(self):
        self.tables = {
            "modules": [
                {"id": 1, "motif_id": 5, "passing_score": 70},
                {"id": 2, "motif_id": 6, "passing_score": 85},
            ]
        }
        self.calls, self.fail_tables, self._id = [], set(), 0

    def next_id(self):
        self._id += 1
        return self._id

    def table(self, name):
        return Query(self, name)


# Item dikirim sebagai dict mentah (seperti JSON dari aplikasi); server memvalidasinya satu per satu.
def quiz(module_id=1, score=80, client_ref=None, attempted_at=None):
    return dict(module_id=module_id, score=score, total_questions=10, attempted_at=attempted_at, client_ref=client_ref)


def practice(module_id=1, confidence=0.8, image_path=None, created_at=None):
    return dict(module_id=module_id, confidence=confidence, image_path=image_path, inference_time_ms=120, created_at=created_at)


def progress(module_id=1, **kw):
    base = dict(module_id=module_id, history_done=False, character_done=False, gallery_done=False,
                quiz_done=False, practice_done=False, quiz_score=None, practice_score=None, last_accessed_at=None)
    base.update(kw)
    return base


def push(db, quiz_attempts=(), practice_results=(), progress_items=()):
    body = SyncPushIn(progress=list(progress_items), quiz_attempts=list(quiz_attempts), practice_results=list(practice_results))
    return process_push(db, 7, body, NOW)


class SyncTests(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)  # log error yang diharapkan dari tes simulasi gagal
        self.addCleanup(logging.disable, logging.NOTSET)
        modules_service._cache.update(at=0.0, data={})
        self.db = FakeDB()

    def prog(self, module_id=1):
        return next((r for r in self.db.tables.get("user_module_progress", []) if r["module_id"] == module_id), None)

    def test_quiz_attempt_uses_server_kkm_and_updates_progress(self):
        out = push(self.db, quiz_attempts=[quiz(1, 80, "a-1"), quiz(2, 80, "a-2")])
        self.assertEqual([r["status"] for r in out["quiz_attempts"]], ["accepted", "accepted"])
        rows = {r["module_id"]: r for r in self.db.tables["quiz_attempts"]}
        self.assertTrue(rows[1]["passed"])      # KKM modul 1 = 70
        self.assertFalse(rows[2]["passed"])     # KKM modul 2 = 85
        self.assertEqual(self.prog(1)["progress_percent"], 20)
        self.assertEqual(self.prog(2)["progress_percent"], 0)
        self.assertEqual(self.prog(2)["quiz_score"], 80)

    def test_duplicate_client_ref_is_not_stored_twice(self):
        push(self.db, quiz_attempts=[quiz(1, 90, "dev-1")])
        out = push(self.db, quiz_attempts=[quiz(1, 90, "dev-1")])
        self.assertEqual(out["quiz_attempts"][0]["status"], "duplicate")
        self.assertEqual(len(self.db.tables["quiz_attempts"]), 1)

    def test_attempts_without_client_ref_are_all_kept(self):
        push(self.db, quiz_attempts=[quiz(1, 50), quiz(1, 60)])
        self.assertEqual(len(self.db.tables["quiz_attempts"]), 2)
        self.assertEqual(self.prog(1)["quiz_score"], 60)

    def test_best_quiz_score_wins(self):
        push(self.db, quiz_attempts=[quiz(1, 90, "x1"), quiz(1, 40, "x2")])
        self.assertEqual(self.prog(1)["quiz_score"], 90)

    def test_unknown_module_rejected_and_batch_continues(self):
        out = push(self.db, quiz_attempts=[quiz(99, 80, "z"), quiz(1, 80, "y")])
        self.assertEqual([r["status"] for r in out["quiz_attempts"]], ["rejected", "accepted"])
        self.assertEqual(out["quiz_attempts"][0]["detail"], "module_id tidak dikenal")

    def test_practice_stored_with_server_verdict_and_progress(self):
        out = push(self.db, practice_results=[practice(1, 0.8, "https://x/y.jpg")])
        self.assertEqual(out["practice_results"][0]["status"], "accepted")
        scan = self.db.tables["scans"][0]
        self.assertEqual((scan["scan_type"], scan["top_motif_id"], scan["passed"]), ("kuismu", 5, True))
        self.assertEqual(scan["image_path"], "https://x/y.jpg")
        self.assertEqual(self.prog(1)["practice_score"], 80)

    def test_local_device_path_is_not_stored(self):
        push(self.db, practice_results=[practice(1, 0.8, "/data/user/0/app/files/foto.jpg")])
        self.assertIsNone(self.db.tables["scans"][0]["image_path"])

    def test_practice_percent_scale_and_fail(self):
        push(self.db, practice_results=[practice(2, 80)])  # 80 (%) < KKM 85
        self.assertFalse(self.db.tables["scans"][0]["passed"])
        self.assertEqual(self.prog(2)["progress_percent"], 0)

    def test_newer_practice_overwrites_single_row_per_module(self):
        push(self.db, practice_results=[practice(1, 0.6, created_at=NOW - timedelta(hours=2))])
        push(self.db, practice_results=[practice(1, 0.9, created_at=NOW - timedelta(hours=1))])
        self.assertEqual(len(self.db.tables["scans"]), 1)
        self.assertAlmostEqual(self.db.tables["scans"][0]["confidence"], 0.9)

    def test_older_practice_keeps_newer_scan_but_best_score_counts(self):
        push(self.db, practice_results=[practice(1, 0.7, created_at=NOW - timedelta(hours=1))])
        out = push(self.db, practice_results=[practice(1, 0.95, created_at=NOW - timedelta(days=1))])
        self.assertEqual(out["practice_results"][0]["status"], "duplicate")
        self.assertAlmostEqual(self.db.tables["scans"][0]["confidence"], 0.7)
        self.assertEqual(self.prog(1)["practice_score"], 95)

    def test_progress_push_merges_flags(self):
        push(self.db, progress_items=[progress(1, history_done=True)])
        out = push(self.db, progress_items=[progress(1, gallery_done=True, character_done=True)])
        self.assertEqual(out["progress"][0]["status"], "accepted")
        row = self.prog(1)
        self.assertEqual((row["history_done"], row["gallery_done"], row["progress_percent"]), (True, True, 60))
        snap = {r["module_id"]: r for r in out["progress_snapshot"]}
        self.assertEqual(snap[1]["progress_percent"], 60)

    def test_full_completion(self):
        push(self.db,
             quiz_attempts=[quiz(1, 80, "q")],
             practice_results=[practice(1, 0.9)],
             progress_items=[progress(1, history_done=True, character_done=True, gallery_done=True)])
        row = self.prog(1)
        self.assertEqual((row["progress_percent"], row["status"], row["is_passed"]), (100, "completed", True))
        self.assertEqual(row["completed_at"], NOW.isoformat())

    def test_temporary_failure_reports_error_for_retry_and_does_not_abort_batch(self):
        self.db.fail_tables.add("scans")
        out = push(self.db, quiz_attempts=[quiz(1, 80, "ok")], practice_results=[practice(1, 0.9)])
        self.assertEqual(out["quiz_attempts"][0]["status"], "accepted")
        self.assertEqual(out["practice_results"][0]["status"], "error")
        self.assertIsNone(self.prog(1) and self.prog(1)["practice_score"])  # praktikum belum tercatat

    def test_invalid_item_is_rejected_alone_and_rest_of_batch_still_saved(self):
        out = push(self.db, quiz_attempts=[quiz(1, 150, "bad"), quiz(1, 60, "ok")])
        bad, ok = out["quiz_attempts"]
        self.assertEqual((bad["status"], ok["status"]), ("rejected", "accepted"))
        self.assertIn("score", bad["detail"])
        self.assertEqual((bad["index"], bad["module_id"], bad["client_ref"]), (0, 1, "bad"))
        self.assertEqual(len(self.db.tables["quiz_attempts"]), 1)  # hanya item valid yang tersimpan
        self.assertEqual(self.prog(1)["quiz_score"], 60)

    def test_malformed_items_never_raise_and_are_rejected(self):
        out = push(self.db, quiz_attempts=["bukan objek", {"module_id": "abc", "score": 50}, 7])
        self.assertEqual([r["status"] for r in out["quiz_attempts"]], ["rejected"] * 3)
        self.assertEqual([r["module_id"] for r in out["quiz_attempts"]], [None, None, None])
        self.assertNotIn("quiz_attempts", self.db.tables)  # tidak ada yang tertulis

    def test_rejection_applies_to_all_three_lists(self):
        out = push(self.db,
                   quiz_attempts=[quiz(0, 50)],
                   practice_results=[practice(1, 500)],
                   progress_items=[progress(1, quiz_score=101), progress(1, history_done=True)])
        self.assertEqual(out["quiz_attempts"][0]["status"], "rejected")
        self.assertEqual(out["practice_results"][0]["status"], "rejected")
        self.assertEqual([r["status"] for r in out["progress"]], ["rejected", "accepted"])
        self.assertEqual(self.prog(1)["history_done"], True)

    def test_retry_after_error_succeeds(self):
        self.db.fail_tables.add("scans")
        push(self.db, practice_results=[practice(1, 0.9)])
        self.db.fail_tables.clear()
        out = push(self.db, practice_results=[practice(1, 0.9)])
        self.assertEqual(out["practice_results"][0]["status"], "accepted")
        self.assertEqual(len(self.db.tables["scans"]), 1)


if __name__ == "__main__":
    unittest.main()
