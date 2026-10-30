import unittest

from app.health import classify_supabase_error


class ConnectError(Exception):  # nama kelas meniru httpx.ConnectError
    pass


class ReadTimeout(Exception):
    pass


class SupabaseException(Exception):
    pass


class APIError(Exception):
    pass


def code(exc):
    return classify_supabase_error(exc)[0]


class ClassifyTests(unittest.TestCase):
    def test_new_key_rejected_by_old_client_or_server(self):
        self.assertEqual(code(SupabaseException("Invalid API key")), "kunci_ditolak")
        self.assertEqual(code(APIError("{'message': 'Invalid API key', 'hint': 'Double check your Supabase `anon` or `service_role` API key.'}")), "kunci_ditolak")
        self.assertEqual(code(APIError("Invalid JWT")), "kunci_ditolak")
        self.assertIn("pip install -U", classify_supabase_error(SupabaseException("Invalid API key"))[1])

    def test_missing_table(self):
        self.assertEqual(code(APIError("{'code': 'PGRST205', 'message': \"Could not find the table 'public.modules' in the schema cache\"}")), "tabel_belum_ada")
        self.assertEqual(code(APIError("relation \"public.modules\" does not exist (42P01)")), "tabel_belum_ada")

    def test_bad_url(self):
        self.assertEqual(code(SupabaseException("Invalid URL")), "url_salah")
        self.assertEqual(code(ValueError("Unsupported protocol in SUPABASE_URL")), "url_salah")

    def test_network_problems(self):
        self.assertEqual(code(ConnectError("[Errno 11001] getaddrinfo failed")), "jaringan")
        self.assertEqual(code(ReadTimeout("")), "jaringan")
        self.assertEqual(code(OSError("Network is unreachable")), "jaringan")
        self.assertEqual(code(Exception("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")), "jaringan")

    def test_permission_and_unknown(self):
        self.assertEqual(code(APIError("permission denied for table users (42501)")), "izin_ditolak")
        self.assertEqual(code(Exception("401 Unauthorized")), "kunci_ditolak")
        self.assertEqual(code(RuntimeError("sesuatu yang aneh")), "tidak_dikenal")

    def test_never_leaks_raw_message(self):
        secret_like = "sb_secret_abcdef1234567890"
        _, hint = classify_supabase_error(APIError(f"Invalid API key: {secret_like}"))
        self.assertNotIn(secret_like, hint)


if __name__ == "__main__":
    unittest.main()
