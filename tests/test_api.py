"""Tes API. Jalankan:  python -m unittest discover -s tests -v"""
import io
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from app.db import connect  # noqa: E402
from app.seed import DEMO_EMAIL, DEMO_PASSWORD, seed_demo_users  # noqa: E402
from app.security import create_token, iso, utcnow  # noqa: E402

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 32


class FixedClassifier:
    """Classifier palsu untuk tes: mengembalikan probabilitas yang sudah ditentukan."""

    def __init__(self, probs):
        self.probs = probs

    def predict(self, image_bytes, class_count):
        return list(self.probs)


def probs_favoring(class_index: int, top: float, n: int = 20) -> list[float]:
    rest = (1 - top) / (n - 1)
    return [top if i == class_index else rest for i in range(n)]


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app(
            {"DATABASE": os.path.join(self.tmp.name, "t.db"), "UPLOAD_DIR": os.path.join(self.tmp.name, "up"), "TESTING": True,
             # jangan ikut membaca .env developer
             "SEED_DEMO_USERS": False, "ALLOW_DEMO_OTP": True, "SMTP_HOST": "", "SMTP_FROM": ""}
        )
        self.client = self.app.test_client()
        self._conns = []

    def tearDown(self):
        for conn in self._conns:
            conn.close()
        self.tmp.cleanup()

    # helpers
    def register(self, email="ani@example.com", name="Ani", password="rahasia123"):
        r = self.client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
        self.assertEqual(r.status_code, 201, r.get_json())
        return {"Authorization": f"Bearer {r.get_json()['token']}"}

    def upload(self, url, headers, data=JPEG, name="foto.jpg"):
        return self.client.post(url, headers=headers, data={"image": (io.BytesIO(data), name)})

    def db(self):
        conn = connect(self.app.config["DATABASE"])
        self._conns.append(conn)
        return conn


class AuthTests(ApiTestCase):
    def test_register_login_me(self):
        h = self.register()
        me = self.client.get("/api/auth/me", headers=h).get_json()["user"]
        self.assertEqual(me["email"], "ani@example.com")
        self.assertNotIn("password_hash", me)
        r = self.client.post("/api/auth/login", json={"email": "ANI@example.com ", "password": "rahasia123"})
        self.assertEqual(r.status_code, 200)

    def test_password_is_hashed_with_scrypt(self):
        self.register()
        stored = self.db().execute("SELECT password_hash FROM users").fetchone()[0]
        self.assertTrue(stored.startswith("scrypt$"))
        self.assertNotIn("rahasia123", stored)

    def test_register_validation(self):
        bad = [
            ({"name": "", "email": "a@b.co", "password": "12345678"}, "name"),
            ({"name": "A", "email": "bukan-email", "password": "12345678"}, "email"),
            ({"name": "A", "email": "a@b.co", "password": "short"}, "password"),
            ({"name": "A", "email": "a@b.co", "password": "x" * 129}, "password"),
        ]
        for body, field in bad:
            r = self.client.post("/api/auth/register", json=body)
            self.assertEqual(r.status_code, 422, body)
            self.assertEqual(r.get_json()["error"]["field"], field)
        self.assertEqual(self.client.post("/api/auth/register", data="bukan json").status_code, 400)

    def test_duplicate_email_case_insensitive(self):
        self.register("ani@example.com")
        r = self.client.post("/api/auth/register", json={"name": "B", "email": "ANI@Example.com", "password": "12345678"})
        self.assertEqual(r.status_code, 409)

    def test_wrong_password_and_unknown_email_same_message(self):
        self.register()
        a = self.client.post("/api/auth/login", json={"email": "ani@example.com", "password": "salahsalah"})
        b = self.client.post("/api/auth/login", json={"email": "tidak@ada.com", "password": "salahsalah"})
        self.assertEqual((a.status_code, b.status_code), (401, 401))
        self.assertEqual(a.get_json()["error"]["message"], b.get_json()["error"]["message"])

    def test_lockout_after_repeated_failures(self):
        self.register()
        for _ in range(4):
            r = self.client.post("/api/auth/login", json={"email": "ani@example.com", "password": "salahsalah"})
            self.assertEqual(r.status_code, 401)
        r = self.client.post("/api/auth/login", json={"email": "ani@example.com", "password": "salahsalah"})
        self.assertEqual(r.status_code, 423)
        # password benar pun ditolak selama terkunci
        r = self.client.post("/api/auth/login", json={"email": "ani@example.com", "password": "rahasia123"})
        self.assertEqual(r.status_code, 423)
        self.assertGreater(r.get_json()["error"]["retry_after_seconds"], 0)
        # setelah lockout lewat, login normal dan penghitung direset
        past = iso(utcnow() - timedelta(minutes=1))
        with self.db() as conn:
            conn.execute("UPDATE users SET lockout_until = ?", (past,))
        r = self.client.post("/api/auth/login", json={"email": "ani@example.com", "password": "rahasia123"})
        self.assertEqual(r.status_code, 200)
        row = self.db().execute("SELECT failed_attempts, lockout_until FROM users").fetchone()
        self.assertEqual(tuple(row), (0, None))

    def test_protected_routes_need_valid_token(self):
        self.assertEqual(self.client.get("/api/modules").status_code, 401)
        self.assertEqual(self.client.get("/api/modules", headers={"Authorization": "Bearer abc"}).status_code, 401)
        self.assertEqual(self.client.get("/api/modules", headers={"Authorization": "Basic abc"}).status_code, 401)

    def test_expired_token_and_deleted_user(self):
        import jwt

        self.register()
        key = self.app.config["SECRET_KEY"]
        expired = jwt.encode({"sub": "1", "exp": utcnow() - timedelta(seconds=5)}, key, algorithm="HS256")
        r = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (401, "token_expired"))
        with self.app.app_context():
            token, _ = create_token(999)  # token sah, tetapi user tidak ada
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code, 401)

    def test_token_signed_with_other_key_rejected(self):
        import jwt

        forged = jwt.encode({"sub": "1", "exp": utcnow() + timedelta(hours=1)}, "kunci-lain-yang-cukup-panjang-xx", algorithm="HS256")
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code, 401)

    def test_token_with_alg_none_rejected(self):
        import base64, json

        def b(d):
            return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

        self.register()
        token = f"{b({'alg': 'none', 'typ': 'JWT'})}.{b({'sub': '1', 'exp': 9999999999})}."
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code, 401)


# Modul uji: 6 = Kawung (kelas 5, 4 soal), 9 = Parang (kelas 8, 8 soal, materi lengkap)
KAWUNG, PARANG = 6, 9


class ModuleTests(ApiTestCase):
    def test_list_has_progress_defaults(self):
        h = self.register()
        mods = self.client.get("/api/modules", headers=h).get_json()["modules"]
        self.assertEqual(len(mods), 20)
        self.assertEqual([m["order_no"] for m in mods], list(range(1, 21)))
        m = mods[0]
        self.assertEqual((m["status"], m["progress_percent"]), ("not_started", 0))
        self.assertIsNone(m["quiz_best_score"])
        self.assertIsNone(m["practice_best_score"])
        self.assertIn("video_url", m)

    def test_detail_has_rich_content_and_no_answers(self):
        h = self.register()
        d = self.client.get(f"/api/modules/{PARANG}", headers=h).get_json()["module"]
        self.assertEqual(d["motif"]["slug"], "batik_parang")
        self.assertTrue(d["video_url"].startswith("https://www.youtube.com/"))
        sej = d["contents"]["sejarah_filosofi"]
        self.assertEqual([c["order_no"] for c in sej], [1, 2, 3, 4])
        kar = d["contents"]["karakteristik"]
        self.assertEqual([c["order_no"] for c in kar][:4], [1, 2, 3, 4])
        self.assertTrue(kar[1]["badge"])  # kartu struktur utama punya badge
        self.assertEqual(len(d["gallery"]), 4)
        self.assertNotIn("correct_option", str(d))

    def test_thin_module_still_has_one_paragraph_per_pillar(self):
        """Seluruh modul kini memiliki konten 3 pilar mendalam (4 sejarah & filosofi, 8 karakteristik)."""
        h = self.register()
        d = self.client.get("/api/modules/1", headers=h).get_json()["module"]
        self.assertEqual(len(d["contents"]["sejarah_filosofi"]), 4)
        self.assertEqual(len(d["contents"]["karakteristik"]), 8)

    def test_pillars_drive_progress_percent(self):
        h = self.register()
        for i, pillar in enumerate(["history", "character", "gallery"], start=1):
            r = self.client.post(f"/api/modules/{KAWUNG}/pillars/{pillar}", headers=h)
            self.assertEqual(r.get_json()["progress"]["progress_percent"], 20 * i)
        self.assertEqual(self.client.post(f"/api/modules/{KAWUNG}/pillars/xx", headers=h).status_code, 404)

    def test_progress_is_per_user(self):
        a = self.register("a@example.com")
        b = self.register("b@example.com")
        self.client.post(f"/api/modules/{KAWUNG}/pillars/history", headers=a)
        mods = {m["id"]: m for m in self.client.get("/api/modules", headers=b).get_json()["modules"]}
        self.assertEqual(mods[KAWUNG]["progress_percent"], 0)


class QuizTests(ApiTestCase):
    def answers(self, h, module=KAWUNG, wrong=0):
        qs = self.client.get(f"/api/modules/{module}/quiz", headers=h).get_json()["questions"]
        with self.db() as conn:
            correct = dict(conn.execute("SELECT id, correct_option FROM quiz_questions WHERE module_id = ?", (module,)).fetchall())
        out = []
        for i, q in enumerate(qs):
            right = correct[q["id"]]
            pick = ("A" if right != "A" else "B") if i < wrong else right
            out.append({"question_id": q["id"], "selected_option": pick})
        return out

    def test_questions_do_not_leak_answers(self):
        h = self.register()
        data = self.client.get(f"/api/modules/{KAWUNG}/quiz", headers=h).get_json()
        self.assertEqual(data["total"], 25)
        self.assertNotIn("correct_option", str(data))
        self.assertNotIn("explanation", str(data))
        self.assertEqual(set(data["questions"][0]["options"]), {"A", "B", "C", "D"})

    def test_pass_marks_quiz_done_and_returns_review(self):
        h = self.register()
        r = self.client.post(f"/api/modules/{KAWUNG}/quiz/attempts", headers=h, json={"answers": self.answers(h)})
        self.assertEqual(r.status_code, 201)
        b = r.get_json()
        self.assertEqual((b["attempt"]["score"], b["attempt"]["passed"]), (100, True))
        self.assertTrue(b["progress"]["quiz_done"])
        self.assertEqual(b["progress"]["quiz_best_score"], 100)
        self.assertTrue(all(x["explanation"] and x["correct_option"] for x in b["results"]))

    def test_fail_does_not_mark_and_pass_is_sticky(self):
        h = self.register()
        # Dari 25 butir soal, salah 13 butir (12 benar) = skor 48% (gagal, < 70)
        r = self.client.post(f"/api/modules/{KAWUNG}/quiz/attempts", headers=h, json={"answers": self.answers(h, wrong=13)})
        b = r.get_json()
        self.assertEqual((b["attempt"]["score"], b["attempt"]["passed"]), (48, False))
        self.assertFalse(b["progress"]["quiz_done"])
        self.client.post(f"/api/modules/{KAWUNG}/quiz/attempts", headers=h, json={"answers": self.answers(h)})
        r = self.client.post(f"/api/modules/{KAWUNG}/quiz/attempts", headers=h, json={"answers": self.answers(h, wrong=25)})
        self.assertTrue(r.get_json()["progress"]["quiz_done"])
        self.assertEqual(r.get_json()["progress"]["quiz_best_score"], 100)

    def test_unanswered_counts_as_wrong(self):
        h = self.register()
        # Menjawab 20 soal benar dari 25 soal di bank = skor 80% (5 soal tidak dijawab dihitung salah)
        r = self.client.post(f"/api/modules/{KAWUNG}/quiz/attempts", headers=h, json={"answers": self.answers(h)[:20]})
        self.assertEqual(r.get_json()["attempt"]["score"], 80)

    def test_answer_validation(self):
        h = self.register()
        url = f"/api/modules/{KAWUNG}/quiz/attempts"
        self.assertEqual(self.client.post(url, headers=h, json={"answers": []}).status_code, 400)
        self.assertEqual(self.client.post(url, headers=h, json={"answers": [{"question_id": 9999, "selected_option": "A"}]}).status_code, 422)
        qid = self.answers(h)[0]["question_id"]
        self.assertEqual(self.client.post(url, headers=h, json={"answers": [{"question_id": qid, "selected_option": "Z"}]}).status_code, 422)
        dup = [{"question_id": qid, "selected_option": "A"}] * 2
        self.assertEqual(self.client.post(url, headers=h, json={"answers": dup}).status_code, 422)

    def test_lowercase_option_accepted(self):
        h = self.register()
        a = self.answers(h)
        a[0]["selected_option"] = a[0]["selected_option"].lower()
        self.assertEqual(self.client.post(f"/api/modules/{KAWUNG}/quiz/attempts", headers=h, json={"answers": a}).status_code, 201)

    def test_parang_has_kusumo_questions(self):
        h = self.register()
        self.assertEqual(self.client.get(f"/api/modules/{PARANG}/quiz", headers=h).get_json()["total"], 25)


class ScanTests(ApiTestCase):
    def set_probs(self, probs):
        self.app.config["CLASSIFIER"] = FixedClassifier(probs)

    def test_universal_scan_top5_and_history(self):
        h = self.register()
        self.set_probs(probs_favoring(8, 0.60))  # kelas 8 = Batik Parang
        r = self.upload("/api/scans/universal", h, PNG, "a.png")
        self.assertEqual(r.status_code, 201, r.get_json())
        b = r.get_json()
        self.assertEqual(b["top_match"]["name"], "Batik Parang")
        self.assertEqual(b["top_match"]["suggested_module"]["id"], PARANG)
        self.assertEqual(len(b["top5"]), 5)
        self.assertEqual([x["rank"] for x in b["top5"]], [1, 2, 3, 4, 5])
        with self.db() as conn:
            s = conn.execute("SELECT * FROM scans").fetchone()
            self.assertEqual((s["scan_type"], s["module_id"], s["passed"]), ("universal", None, None))
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM scan_probabilities").fetchone()[0], 20)
            self.assertAlmostEqual(conn.execute("SELECT SUM(probability) FROM scan_probabilities").fetchone()[0], 1, places=4)
        self.assertTrue(os.path.exists(os.path.join(self.app.config["UPLOAD_DIR"], s["image_path"])))
        hist = self.client.get("/api/scans", headers=h).get_json()
        self.assertEqual(hist["scans"][0]["motif_name"], "Batik Parang")
        self.assertFalse(hist["scans"][0]["passed"])  # 0.60 < ambang 0.70

    def test_universal_history_passed_threshold(self):
        h = self.register()
        self.set_probs(probs_favoring(8, 0.85))
        self.upload("/api/scans/universal", h)
        self.assertTrue(self.client.get("/api/scans", headers=h).get_json()["scans"][0]["passed"])

    def test_image_validation(self):
        h = self.register()
        self.assertEqual(self.client.post("/api/scans/universal", headers=h).status_code, 400)
        self.assertEqual(self.upload("/api/scans/universal", h, b"bukan gambar", "x.jpg").status_code, 415)
        self.assertEqual(self.upload("/api/scans/universal", h, b"", "x.jpg").status_code, 400)

    def test_upload_size_limit(self):
        h = self.register()
        self.app.config["MAX_CONTENT_LENGTH"] = 1024
        self.assertEqual(self.upload("/api/scans/universal", h, JPEG + b"\x00" * 4096).status_code, 413)

    def test_practice_pass_marks_practice_done(self):
        h = self.register()
        self.set_probs(probs_favoring(5, 0.82))  # kelas 5 = Kawung = modul 6
        r = self.upload(f"/api/modules/{KAWUNG}/practice", h)
        self.assertEqual(r.status_code, 201, r.get_json())
        b = r.get_json()
        self.assertTrue(b["scan"]["passed"])
        self.assertEqual(b["scan"]["rating"], "sangat_mirip")
        self.assertEqual(b["target_motif"]["name"], "Batik Kawung")
        self.assertTrue(b["progress"]["practice_done"])
        self.assertEqual(b["progress"]["practice_best_score"], 82)
        self.assertEqual(len(b["ranking"]), 20)

    def test_practice_fail_and_ratings(self):
        h = self.register()
        n = 20
        for fit, rating, passed in [(0.60, "cukup_mirip", False), (0.30, "perlu_dilatih", False)]:
            probs = [(1 - fit - 0.1) / (n - 2)] * n
            probs[5], probs[0] = fit, 0.1
            self.set_probs(probs)
            b = self.upload(f"/api/modules/{KAWUNG}/practice", h).get_json()
            self.assertEqual((b["scan"]["rating"], b["scan"]["passed"]), (rating, passed))
            self.assertFalse(b["progress"]["practice_done"])

    def test_full_module_completion(self):
        h = self.register()
        for pillar in ("history", "character", "gallery"):
            self.client.post(f"/api/modules/{KAWUNG}/pillars/{pillar}", headers=h)
        QuizTests.answers  # noqa: B018  (dipakai lewat helper di bawah)
        qs = self.client.get(f"/api/modules/{KAWUNG}/quiz", headers=h).get_json()["questions"]
        with self.db() as conn:
            correct = dict(conn.execute("SELECT id, correct_option FROM quiz_questions WHERE module_id = ?", (KAWUNG,)).fetchall())
        ans = [{"question_id": q["id"], "selected_option": correct[q["id"]]} for q in qs]
        self.client.post(f"/api/modules/{KAWUNG}/quiz/attempts", headers=h, json={"answers": ans})
        self.set_probs(probs_favoring(5, 0.9))
        self.upload(f"/api/modules/{KAWUNG}/practice", h)
        stats = self.client.get("/api/profile", headers=h).get_json()
        self.assertEqual(stats["stats"]["completed_modules"], 1)
        self.assertEqual(stats["stats"]["total_modules"], 20)
        self.assertEqual(stats["stats"]["overall_progress_percent"], 5)

    def test_model_output_mismatch_is_rejected_and_nothing_stored(self):
        h = self.register()
        self.set_probs([0.5, 0.5])
        r = self.upload("/api/scans/universal", h)
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (500, "model_mismatch"))
        self.assertEqual(self.db().execute("SELECT COUNT(*) FROM scans").fetchone()[0], 0)
        self.assertEqual(os.listdir(self.app.config["UPLOAD_DIR"]), [])

    def test_scans_are_private_to_owner(self):
        a, b = self.register("a@example.com"), self.register("b@example.com")
        self.set_probs(probs_favoring(8, 0.8))
        sid = self.upload("/api/scans/universal", a).get_json()["scan"]["id"]
        self.assertEqual(self.client.get(f"/api/scans/{sid}", headers=a).status_code, 200)
        self.assertEqual(self.client.get(f"/api/scans/{sid}", headers=b).status_code, 404)
        self.assertEqual(self.client.get(f"/api/scans/{sid}/image", headers=b).status_code, 404)
        self.assertEqual(self.client.get("/api/scans", headers=b).get_json()["total"], 0)

    def test_history_filter_and_pagination_params(self):
        h = self.register()
        self.set_probs(probs_favoring(8, 0.8))
        self.upload("/api/scans/universal", h)
        self.upload(f"/api/modules/{PARANG}/practice", h)
        self.assertEqual(self.client.get("/api/scans?type=kuismu", headers=h).get_json()["total"], 1)
        self.assertEqual(self.client.get("/api/scans?type=universal", headers=h).get_json()["total"], 1)
        self.assertEqual(self.client.get("/api/scans?type=x", headers=h).status_code, 422)
        self.assertEqual(self.client.get("/api/scans?limit=abc", headers=h).status_code, 422)


    def test_practice_quiz_auto_prunes_previous_image(self):
        h = self.register("prune_user@example.com")
        self.set_probs(probs_favoring(5, 0.82))

        # Percobaan 1 kuis praktik Kawung
        r1 = self.upload(f"/api/modules/{KAWUNG}/practice", h, JPEG, "foto1.jpg")
        self.assertEqual(r1.status_code, 201)
        uid = self.db().execute("SELECT id FROM users WHERE email='prune_user@example.com'").fetchone()[0]
        s1 = self.db().execute("SELECT id, image_path FROM scans WHERE user_id = ? AND scan_type = 'kuismu'", (uid,)).fetchone()
        s1_id = s1["id"]
        s1_path = s1["image_path"]
        self.assertIsNotNone(s1_path)
        full_s1_path = os.path.join(self.app.config["UPLOAD_DIR"], s1_path)
        self.assertTrue(os.path.exists(full_s1_path))

        # Percobaan 2 kuis praktik Kawung pada modul yang sama
        r2 = self.upload(f"/api/modules/{KAWUNG}/practice", h, PNG, "foto2.png")
        self.assertEqual(r2.status_code, 201)
        scans = self.db().execute("SELECT id, image_path FROM scans WHERE user_id = ? AND scan_type = 'kuismu' ORDER BY id", (uid,)).fetchall()

        self.assertEqual(len(scans), 2)
        # Scan pertama image_path diubah jadi NULL
        self.assertIsNone(scans[0]["image_path"])
        # File foto pertama di disk harus terhapus fisik (auto-prune)
        self.assertFalse(os.path.exists(full_s1_path))
        # Scan kedua memiliki file foto baru yang tersimpan
        self.assertIsNotNone(scans[1]["image_path"])
        self.assertTrue(os.path.exists(os.path.join(self.app.config["UPLOAD_DIR"], scans[1]["image_path"])))

        # Unduh gambar scan 1 -> 404 (karena sudah tertimpa/dibersihkan)
        self.assertEqual(self.client.get(f"/api/scans/{s1_id}/image", headers=h).status_code, 404)
        # Unduh gambar scan 2 -> 200
        r_img2 = self.client.get(f"/api/scans/{scans[1]['id']}/image", headers=h)
        self.assertEqual(r_img2.status_code, 200)
        r_img2.close()

class PasswordResetTests(ApiTestCase):
    def request_otp(self, email="ani@example.com"):
        return self.client.post("/api/auth/forgot-password", json={"email": email})

    def test_full_flow_demo_mode_and_new_password_works(self):
        self.register()
        r = self.request_otp()
        self.assertEqual(r.status_code, 200)
        b = r.get_json()
        self.assertEqual(b["delivery"], "demo")
        otp = b["demo_otp"]
        self.assertRegex(otp, r"^\d{4}$")
        stored = self.db().execute("SELECT otp_hash FROM password_resets").fetchone()[0]
        self.assertNotIn(otp, stored)  # OTP tidak disimpan polos
        v = self.client.post("/api/auth/verify-otp", json={"email": "ani@example.com", "otp": otp})
        self.assertEqual(v.status_code, 200)
        token = v.get_json()["reset_token"]
        r = self.client.post("/api/auth/reset-password", json={"email": "ani@example.com", "reset_token": token, "new_password": "sandibaru99"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "ani@example.com", "password": "sandibaru99"}).status_code, 200)
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "ani@example.com", "password": "rahasia123"}).status_code, 401)
        # token sekali pakai
        r = self.client.post("/api/auth/reset-password", json={"email": "ani@example.com", "reset_token": token, "new_password": "lagi12345"})
        self.assertEqual(r.status_code, 422)

    def test_unknown_email_and_validation(self):
        self.assertEqual(self.request_otp("tidak@ada.com").status_code, 404)
        self.assertEqual(self.request_otp("bukan-email").status_code, 422)

    def test_demo_otp_refused_when_disabled_and_no_smtp(self):
        self.register()
        self.app.config["ALLOW_DEMO_OTP"] = False
        r = self.request_otp()
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (503, "email_not_configured"))
        self.assertNotIn("demo_otp", str(r.get_json()))

    def test_wrong_otp_limited_attempts(self):
        self.register()
        self.request_otp()
        for left in (4, 3, 2, 1, 0):
            r = self.client.post("/api/auth/verify-otp", json={"email": "ani@example.com", "otp": "0000"})
            self.assertEqual(r.get_json()["error"]["attempts_left"], left) if r.status_code == 422 else None
        r = self.client.post("/api/auth/verify-otp", json={"email": "ani@example.com", "otp": "0000"})
        self.assertEqual(r.status_code, 429)

    def test_expired_otp_and_throttle(self):
        self.register()
        otp = self.request_otp().get_json()["demo_otp"]
        self.assertEqual(self.request_otp().status_code, 429)  # terlalu cepat
        with self.db() as conn:
            conn.execute("UPDATE password_resets SET expires_at = ?", (iso(utcnow() - timedelta(seconds=1)),))
        r = self.client.post("/api/auth/verify-otp", json={"email": "ani@example.com", "otp": otp})
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (422, "otp_expired"))

    def test_reset_requires_verified_token(self):
        self.register()
        self.request_otp()
        r = self.client.post("/api/auth/reset-password", json={"email": "ani@example.com", "reset_token": "tebakan", "new_password": "sandibaru99"})
        self.assertEqual(r.status_code, 422)

    def test_reset_clears_lockout(self):
        self.register()
        with self.db() as conn:
            conn.execute("UPDATE users SET lockout_until = ?", (iso(utcnow() + timedelta(minutes=10)),))
        otp = self.request_otp().get_json()["demo_otp"]
        tok = self.client.post("/api/auth/verify-otp", json={"email": "ani@example.com", "otp": otp}).get_json()["reset_token"]
        self.client.post("/api/auth/reset-password", json={"email": "ani@example.com", "reset_token": tok, "new_password": "sandibaru99"})
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "ani@example.com", "password": "sandibaru99"}).status_code, 200)

    def test_smtp_path_sends_email_and_hides_otp(self):
        self.register()
        self.app.config.update(SMTP_HOST="smtp.test", SMTP_FROM="noreply@test")
        sent = []
        from app.services import mailer
        original = mailer.send_otp_email
        mailer.send_otp_email = lambda to, name, otp: sent.append((to, otp))
        try:
            b = self.request_otp().get_json()
        finally:
            mailer.send_otp_email = original
        self.assertEqual(b["delivery"], "email")
        self.assertNotIn("demo_otp", b)
        self.assertEqual(sent[0][0], "ani@example.com")


class ProfileTests(ApiTestCase):
    def test_update_name_phone_and_password(self):
        h = self.register()
        r = self.client.patch("/api/profile", headers=h, json={"name": " Budi ", "phone": "081234567890", "password": ""})
        self.assertEqual(r.status_code, 200, r.get_json())
        u = r.get_json()["user"]
        self.assertEqual((u["name"], u["phone"], u["email"]), ("Budi", "081234567890", "ani@example.com"))
        self.assertEqual(self.client.get("/api/auth/me", headers=h).get_json()["user"]["phone"], "081234567890")
        self.client.patch("/api/profile", headers=h, json={"password": "passbaru123"})
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "ani@example.com", "password": "passbaru123"}).status_code, 200)
        self.assertIsNone(self.client.patch("/api/profile", headers=h, json={"phone": ""}).get_json()["user"]["phone"])

    def test_validation_and_duplicate_email(self):
        h = self.register()
        self.register("lain@example.com")
        for body in ({"name": ""}, {"email": "salah"}, {"phone": "abc"}, {"password": "pendek"}):
            self.assertEqual(self.client.patch("/api/profile", headers=h, json=body).status_code, 422, body)
        r = self.client.patch("/api/profile", headers=h, json={"email": "LAIN@example.com"})
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (409, "email_taken"))

    def test_requires_auth(self):
        self.assertEqual(self.client.patch("/api/profile", json={"name": "x"}).status_code, 401)


    def test_avatar_upload_get_and_delete(self):
        h = self.register("avatar_user@example.com")

        # 1. GET avatar saat belum ada -> 404
        r = self.client.get("/api/profile/avatar", headers=h)
        self.assertEqual(r.status_code, 404)

        # 2. Upload avatar pertama kali
        r = self.client.post("/api/profile/avatar", headers=h, data={"avatar": (io.BytesIO(JPEG), "ava.jpg")})
        self.assertEqual(r.status_code, 200, r.get_json())
        user_data = r.get_json()["user"]
        self.assertIsNotNone(user_data["profile_image_path"])
        first_ava_path = user_data["profile_image_path"]

        # Verifikasi file ada di piringan cakram UPLOAD_DIR
        full_first_path = os.path.join(self.app.config["UPLOAD_DIR"], first_ava_path)
        self.assertTrue(os.path.exists(full_first_path))

        # 3. GET avatar -> 200, tutup response handle untuk Windows file lock
        r_get = self.client.get("/api/profile/avatar", headers=h)
        self.assertEqual(r_get.status_code, 200)
        r_get.close()

        # 4. Upload avatar kedua kali -> file avatar pertama harus terhapus fisik (auto-prune)
        r2 = self.client.post("/api/profile/avatar", headers=h, data={"avatar": (io.BytesIO(PNG), "ava2.png")})
        self.assertEqual(r2.status_code, 200)
        second_ava_path = r2.get_json()["user"]["profile_image_path"]
        self.assertNotEqual(first_ava_path, second_ava_path)
        self.assertFalse(os.path.exists(full_first_path))  # File lama terhapus
        self.assertTrue(os.path.exists(os.path.join(self.app.config["UPLOAD_DIR"], second_ava_path)))

        # 5. DELETE avatar -> 200 dan file fisik terhapus
        r_del = self.client.delete("/api/profile/avatar", headers=h)
        self.assertEqual(r_del.status_code, 200)
        self.assertIsNone(r_del.get_json()["user"]["profile_image_path"])
        self.assertFalse(os.path.exists(os.path.join(self.app.config["UPLOAD_DIR"], second_ava_path)))

        # 6. GET avatar kembali 404
        self.assertEqual(self.client.get("/api/profile/avatar", headers=h).status_code, 404)

class SchemaAndSeedTests(ApiTestCase):
    def test_all_tables_present(self):
        names = {r[0] for r in self.db().execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        self.assertEqual(
            names,
            {"users", "batik_motifs", "modules", "module_contents", "module_gallery_images", "quiz_questions",
             "user_module_progress", "quiz_attempts", "quiz_attempt_answers", "scans", "scan_probabilities",
             "password_resets"},
        )
        self.assertIn("phone", {r[1] for r in self.db().execute("PRAGMA table_info(users)")})
        self.assertIn("video_url", {r[1] for r in self.db().execute("PRAGMA table_info(modules)")})
        self.assertIn("badge", {r[1] for r in self.db().execute("PRAGMA table_info(module_contents)")})

    def test_motifs_match_ml_labels_exactly(self):
        """Urutan & nama kelas di DB harus identik dengan labels.txt (output model)."""
        labels_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "models", "labels.txt")
        with open(labels_path, encoding="utf-8") as f:
            labels = [line.strip() for line in f if line.strip()]
        rows = self.db().execute("SELECT slug, ml_class_index FROM batik_motifs ORDER BY ml_class_index").fetchall()
        self.assertEqual(len(labels), 20)
        self.assertEqual([r["ml_class_index"] for r in rows], list(range(20)))
        self.assertEqual([r["slug"] for r in rows], labels)

    def test_every_module_is_complete(self):
        conn = self.db()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM modules").fetchone()[0], 20)
        for mid in range(1, 21):
            pillars = {r[0] for r in conn.execute("SELECT DISTINCT pillar FROM module_contents WHERE module_id = ?", (mid,))}
            self.assertTrue({"sejarah_filosofi", "karakteristik"} <= pillars, mid)
            self.assertGreaterEqual(conn.execute("SELECT COUNT(*) FROM quiz_questions WHERE module_id = ?", (mid,)).fetchone()[0], 4, mid)

    def test_no_placeholder_or_dead_references_in_data(self):
        conn = self.db()
        text = " ".join(str(v) for t in ("batik_motifs", "modules", "module_contents", "quiz_questions")
                        for row in conn.execute(f"SELECT * FROM {t}") for v in row)
        self.assertNotIn("VERIFIKASI", text)
        self.assertNotIn("/static/", text)  # file yang tidak ada
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 0)  # tanpa akun/percobaan palsu
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM quiz_attempts").fetchone()[0], 0)

    def test_constraints_enforced(self):
        conn = self.db()
        now = "2026-01-01T00:00:00Z"
        conn.execute("INSERT INTO users (name,email,password_hash,created_at,updated_at) VALUES ('a','a@x.com','h',?,?)", (now, now))
        bad_sql = [
            "INSERT INTO scans (user_id,scan_type,created_at) VALUES (1,'kuismu','x')",
            "INSERT INTO scans (user_id,scan_type,created_at) VALUES (1,'bukan-tipe','x')",
            "INSERT INTO modules (motif_id,title,description,order_no) VALUES (999,'t','d',99)",
            "INSERT INTO quiz_questions (module_id,question,option_a,option_b,option_c,option_d,correct_option) VALUES (3,'q','a','b','c','d','E')",
            "INSERT INTO user_module_progress (user_id,module_id,status,last_accessed_at) VALUES (1,1,'selesai','x')",
            "INSERT INTO user_module_progress (user_id,module_id,progress_percent,last_accessed_at) VALUES (1,1,120,'x')",
            "INSERT INTO batik_motifs (name,slug,origin_region,short_description,ml_class_index) VALUES ('n','batik_kawung','o','d',77)",
            "INSERT INTO batik_motifs (name,slug,origin_region,short_description,ml_class_index) VALUES ('n','baru','o','d',0)",
            "INSERT INTO users (name,email,password_hash,created_at,updated_at) VALUES ('b','A@X.COM','h','x','x')",  # email NOCASE
        ]
        for sql in bad_sql:
            with self.assertRaises(sqlite3.IntegrityError, msg=sql):
                conn.execute(sql)
        conn.execute("INSERT INTO user_module_progress (user_id,module_id,last_accessed_at) VALUES (1,1,'x')")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO user_module_progress (user_id,module_id,last_accessed_at) VALUES (1,1,'x')")

    def test_seed_is_not_duplicated_on_restart(self):
        app2 = create_app({"DATABASE": self.app.config["DATABASE"], "UPLOAD_DIR": self.app.config["UPLOAD_DIR"], "TESTING": True,
                           "SEED_DEMO_USERS": False})
        self.assertIsNotNone(app2)
        self.assertEqual(self.db().execute("SELECT COUNT(*) FROM batik_motifs").fetchone()[0], 20)

    def test_demo_users_are_idempotent_and_can_login(self):
        with self.db() as conn:
            self.assertEqual(seed_demo_users(conn), 2)
            self.assertEqual(seed_demo_users(conn), 0)
        r = self.client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["user"]["phone"], "081234567890")

    def test_old_v1_database_is_migrated(self):
        """Database inisialisasi pada skema versi 1 definitif."""
        path = os.path.join(self.tmp.name, "old.db")
        from app.db import init_db
        init_db(path)
        conn = sqlite3.connect(path)
        try:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
            self.assertIn("phone", cols)
            self.assertIn("profile_image_path", cols)
            self.assertIn("video_url", {r[1] for r in conn.execute("PRAGMA table_info(modules)")})
            self.assertIn("badge", {r[1] for r in conn.execute("PRAGMA table_info(module_contents)")})
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
        finally:
            conn.close()

    def test_health_and_json_errors(self):
        self.assertEqual(self.client.get("/api/health").get_json(), {"status": "ok"})
        r = self.client.get("/api/tidak-ada")
        self.assertEqual(r.status_code, 404)
        self.assertIn("error", r.get_json())
        self.assertEqual(self.client.delete("/api/health").status_code, 405)



if __name__ == "__main__":
    unittest.main()
