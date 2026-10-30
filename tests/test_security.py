import base64
import hashlib
import unittest
from datetime import datetime, timedelta, timezone

import jwt

from app.config import Settings
from app.security import (
    constant_time_equal,
    create_access_token,
    decode_access_token,
    generate_otp,
    hash_otp,
    hash_password,
    hash_token,
    needs_rehash,
    verify_password,
)

SETTINGS = Settings(jwt_secret="s" * 48, access_token_minutes=30)


class PasswordTests(unittest.TestCase):
    def test_roundtrip_and_unique_salt(self):
        a, b = hash_password("Batikmu123#"), hash_password("Batikmu123#")
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("scrypt$16384$8$1$"))
        self.assertTrue(verify_password("Batikmu123#", a))
        self.assertFalse(verify_password("batikmu123#", a))
        self.assertFalse(needs_rehash(a))

    def test_compatible_with_existing_scrypt_format(self):
        # Hash dibuat mandiri dengan format yang sama seperti data bawaan aplikasi.
        salt = b"0123456789abcdef"
        digest = hashlib.scrypt(b"rahasia-123", salt=salt, n=16384, r=8, p=1, dklen=32)
        stored = "scrypt$16384$8$1$%s$%s" % (base64.b64encode(salt).decode(), base64.b64encode(digest).decode())
        self.assertTrue(verify_password("rahasia-123", stored))
        self.assertFalse(verify_password("salah", stored))

    def test_legacy_sha256_from_mobile_still_verifies_and_needs_rehash(self):
        legacy = hashlib.sha256(("kenali_batikmu_salt_2026" + "Batikmu123#").encode()).hexdigest()
        self.assertEqual(len(legacy), 64)
        self.assertTrue(verify_password("Batikmu123#", legacy))
        self.assertTrue(verify_password("Batikmu123#", legacy.upper()))
        self.assertFalse(verify_password("lain", legacy))
        self.assertTrue(needs_rehash(legacy))

    def test_garbage_hashes_are_rejected_not_raised(self):
        for bad in (None, "", "plain", "scrypt$x$y", "scrypt$3$8$1$AAAA$AAAA", "scrypt$16384$8$1$!!$!!"):
            self.assertFalse(verify_password("apa saja", bad))


class TokenTests(unittest.TestCase):
    def test_access_token_roundtrip(self):
        token, expires_in = create_access_token(42, SETTINGS)
        self.assertEqual(expires_in, 1800)
        self.assertEqual(decode_access_token(token, SETTINGS), 42)

    def test_expired_token(self):
        old = datetime.now(timezone.utc) - timedelta(hours=2)
        token, _ = create_access_token(1, SETTINGS, now=old)
        with self.assertRaises(jwt.ExpiredSignatureError):
            decode_access_token(token, SETTINGS)

    def test_wrong_secret_and_wrong_type_and_alg_none(self):
        token, _ = create_access_token(1, SETTINGS)
        with self.assertRaises(jwt.InvalidSignatureError):
            decode_access_token(token, Settings(jwt_secret="x" * 48))
        now = int(datetime.now(timezone.utc).timestamp())
        refresh_like = jwt.encode({"sub": "1", "type": "refresh", "exp": now + 60}, SETTINGS.jwt_secret, "HS256")
        with self.assertRaises(jwt.InvalidTokenError):
            decode_access_token(refresh_like, SETTINGS)
        none_alg = jwt.encode({"sub": "1", "type": "access", "exp": now + 60}, None, algorithm="none")
        with self.assertRaises(jwt.InvalidTokenError):
            decode_access_token(none_alg, SETTINGS)

    def test_non_numeric_subject(self):
        now = int(datetime.now(timezone.utc).timestamp())
        t = jwt.encode({"sub": "abc", "type": "access", "exp": now + 60}, SETTINGS.jwt_secret, "HS256")
        with self.assertRaises(jwt.InvalidTokenError):
            decode_access_token(t, SETTINGS)


class OtpTests(unittest.TestCase):
    def test_otp_shape_and_hash_binding(self):
        otp = generate_otp(4)
        self.assertRegex(otp, r"^\d{4}$")
        h = hash_otp("1234", 7, "secret")
        self.assertTrue(constant_time_equal(h, hash_otp("1234", 7, "secret")))
        self.assertFalse(constant_time_equal(h, hash_otp("1234", 8, "secret")))  # terikat ke user
        self.assertFalse(constant_time_equal(h, hash_otp("1235", 7, "secret")))

    def test_token_hash_is_stable_and_not_plain(self):
        self.assertEqual(hash_token("abc"), hash_token("abc"))
        self.assertNotIn("abc", hash_token("abc"))


if __name__ == "__main__":
    unittest.main()
