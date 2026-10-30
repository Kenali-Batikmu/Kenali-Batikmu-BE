import unittest
from datetime import datetime, timedelta, timezone

from app.domain import (
    calc_progress,
    clamp_ts,
    detect_image_type,
    merge_progress,
    normalize_confidence,
    parse_ts,
)

NOW = datetime(2026, 10, 27, 3, 0, 0, tzinfo=timezone.utc)


def calc(**kw):
    base = dict(
        history_done=False, character_done=False, gallery_done=False,
        quiz_done=False, quiz_score=None, practice_done=False, practice_score=None, passing_score=70,
    )
    base.update(kw)
    return calc_progress(**base)


class CalcProgressTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(calc(), (0, "not_started", False))

    def test_reading_only_is_three_components(self):
        self.assertEqual(calc(history_done=True, character_done=True, gallery_done=True), (60, "in_progress", False))

    def test_quiz_counts_only_when_score_meets_kkm(self):
        self.assertEqual(calc(quiz_done=True, quiz_score=69)[0], 0)
        self.assertEqual(calc(quiz_done=True, quiz_score=70)[0], 20)

    def test_failed_attempt_alone_stays_not_started_like_the_app(self):
        self.assertEqual(calc(quiz_done=True, quiz_score=10), (0, "not_started", False))

    def test_all_five_complete(self):
        r = calc(history_done=True, character_done=True, gallery_done=True,
                 quiz_done=True, quiz_score=80, practice_done=True, practice_score=75)
        self.assertEqual(r, (100, "completed", True))

    def test_custom_passing_score(self):
        self.assertEqual(calc(quiz_done=True, quiz_score=80, passing_score=85)[0], 0)


class MergeProgressTests(unittest.TestCase):
    def test_new_row(self):
        row = merge_progress(None, {"history_done": True}, 70, NOW)
        self.assertEqual((row["progress_percent"], row["status"]), (20, "in_progress"))
        self.assertIsNone(row["completed_at"])
        self.assertEqual(row["synced_at"], NOW.isoformat())

    def test_never_regresses(self):
        existing = {"history_done": True, "quiz_done": True, "quiz_score": 90, "last_accessed_at": NOW.isoformat()}
        row = merge_progress(existing, {"history_done": False, "quiz_score": 40}, 70, NOW)
        self.assertTrue(row["history_done"])
        self.assertEqual(row["quiz_score"], 90)

    def test_score_implies_done(self):
        row = merge_progress(None, {"practice_score": 88}, 70, NOW)
        self.assertTrue(row["practice_done"])
        self.assertEqual(row["progress_percent"], 20)

    def test_idempotent(self):
        incoming = {"history_done": True, "quiz_score": 75}
        once = merge_progress(None, incoming, 70, NOW)
        twice = merge_progress(once, incoming, 70, NOW + timedelta(minutes=5))
        for k in ("progress_percent", "status", "quiz_score", "history_done", "quiz_done"):
            self.assertEqual(once[k], twice[k])

    def test_order_independent_across_devices(self):
        a = {"history_done": True, "quiz_score": 60}
        b = {"gallery_done": True, "quiz_score": 80, "practice_score": 90}
        ab = merge_progress(merge_progress(None, a, 70, NOW), b, 70, NOW)
        ba = merge_progress(merge_progress(None, b, 70, NOW), a, 70, NOW)
        for k in ("progress_percent", "quiz_score", "practice_score", "history_done", "gallery_done"):
            self.assertEqual(ab[k], ba[k])

    def test_completed_at_set_once(self):
        full = {"history_done": True, "character_done": True, "gallery_done": True, "quiz_score": 80, "practice_score": 80}
        first = merge_progress(None, full, 70, NOW)
        self.assertEqual(first["completed_at"], NOW.isoformat())
        later = merge_progress(first, full, 70, NOW + timedelta(days=1))
        self.assertEqual(later["completed_at"], NOW.isoformat())

    def test_last_accessed_takes_latest_and_clamps_future(self):
        yesterday = NOW - timedelta(days=1)
        row = merge_progress({"last_accessed_at": NOW.isoformat()}, {"last_accessed_at": yesterday}, 70, NOW)
        self.assertEqual(row["last_accessed_at"], NOW.isoformat())
        future = NOW + timedelta(days=30)
        row = merge_progress(None, {"last_accessed_at": future}, 70, NOW)
        self.assertEqual(row["last_accessed_at"], NOW.isoformat())


class HelperTests(unittest.TestCase):
    def test_normalize_confidence(self):
        self.assertEqual(normalize_confidence(0.7), (0.7, 70))
        self.assertEqual(normalize_confidence(70), (0.7, 70))
        self.assertEqual(normalize_confidence(1.0), (1.0, 100))
        self.assertEqual(normalize_confidence(0.705)[1], 71)  # pembulatan seperti Dart (setengah ke atas)
        self.assertEqual(normalize_confidence(0)[1], 0)

    def test_parse_and_clamp_ts(self):
        self.assertEqual(parse_ts("2026-10-27T03:00:00Z"), NOW)
        self.assertEqual(parse_ts("2026-10-27T10:00:00+07:00"), NOW)
        self.assertEqual(parse_ts("2026-10-27T03:00:00"), NOW)  # tanpa zona dianggap UTC
        self.assertEqual(parse_ts("2026-10-27T03:00:00.12345+00:00"), NOW.replace(microsecond=123450))
        self.assertIsNone(parse_ts("bukan tanggal"))
        self.assertIsNone(parse_ts(None))
        self.assertEqual(clamp_ts(None, NOW), NOW)
        self.assertEqual(clamp_ts("sampah", NOW), NOW)
        self.assertEqual(clamp_ts(NOW + timedelta(hours=1), NOW), NOW)
        past = NOW - timedelta(days=3)
        self.assertEqual(clamp_ts(past, NOW), past)

    def test_detect_image_type(self):
        self.assertEqual(detect_image_type(b"\xff\xd8\xff\xe0abc"), ("jpg", "image/jpeg"))
        self.assertEqual(detect_image_type(b"\x89PNG\r\n\x1a\nxxxx"), ("png", "image/png"))
        self.assertIsNone(detect_image_type(b"GIF89a"))
        self.assertIsNone(detect_image_type(b"<svg></svg>"))
        self.assertIsNone(detect_image_type(b""))


if __name__ == "__main__":
    unittest.main()
