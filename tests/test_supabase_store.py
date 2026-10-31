import json
import hashlib
import unittest
from unittest.mock import patch

from supabase_store import SupabaseStoreError, SupabaseUsageLimit, SupabaseUsageStore, create_usage_store


class FakeResponse:
    def __init__(self, body):
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, limit=-1):
        return self.body[:limit]


class SupabaseStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = SupabaseUsageStore(
            url="https://project.supabase.co",
            service_key="server-only-test-key",
        )

    def test_reserve_uses_rpc_and_returns_reservation(self):
        payload = {"request_id": "abc-123", "day": "2026-10-31",
                   "subject_hash": "user-hash", "reserved_tokens": 321}
        with patch("urllib.request.urlopen", return_value=FakeResponse(json.dumps(payload).encode())) as opener:
            result = self.store.reserve("user-hash", 321)
        self.assertEqual(result, payload)
        request = opener.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/rest/v1/rpc/nesil_reserve_usage"))
        self.assertEqual(request.get_header("Apikey"), "server-only-test-key")
        self.assertEqual(json.loads(request.data)["p_estimated_tokens"], 321)
        self.assertEqual(json.loads(request.data)["p_subject_hash"], hashlib.sha256(b"user-hash").hexdigest())

    def test_rpc_failure_classification_identifies_schema_and_permission_roots(self):
        from supabase_store import _rpc_failure_category
        self.assertEqual(_rpc_failure_category(404, "PGRST202"), "rpc_missing_or_signature_mismatch")
        self.assertEqual(_rpc_failure_category(403, "42501"), "rpc_permission_denied")
        self.assertEqual(_rpc_failure_category(503, ""), "supabase_backend_error")

    def test_finish_uses_request_id_only(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"null")) as opener:
            self.store.finish({"request_id": "abc-123"}, 123, 0)
        request = opener.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/rest/v1/rpc/nesil_finish_usage"))
        self.assertEqual(json.loads(request.data)["p_actual_tokens"], 123)

    def test_missing_credentials_fail_closed(self):
        with self.assertRaises(SupabaseStoreError):
            SupabaseUsageStore(url="", service_key="")

    def test_non_https_remote_url_rejected(self):
        with self.assertRaises(SupabaseStoreError):
            SupabaseUsageStore(url="http://example.com", service_key="secret")

    def test_backend_selection_is_explicit(self):
        with patch.dict("os.environ", {"NESIL_STORAGE_BACKEND": "unknown"}):
            with self.assertRaises(ValueError):
                create_usage_store(secrets={})

    def test_streamlit_secrets_are_used_for_supabase_configuration(self):
        secrets = {
            "NESIL_STORAGE_BACKEND": "supabase",
            "SUPABASE_URL": "https://secrets-project.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "server-only-secret-test",
        }
        with patch.dict("os.environ", {}, clear=True):
            store = create_usage_store(secrets=secrets)
        self.assertIsInstance(store, SupabaseUsageStore)
        self.assertEqual(store.url, "https://secrets-project.supabase.co")
        self.assertEqual(store.service_key, "server-only-secret-test")

    def test_environment_variables_are_fallback_for_secrets(self):
        with patch.dict("os.environ", {
            "NESIL_STORAGE_BACKEND": "supabase",
            "SUPABASE_URL": "https://environment-project.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "environment-secret-test",
        }, clear=True):
            store = create_usage_store(secrets={})
        self.assertEqual(store.url, "https://environment-project.supabase.co")
        self.assertEqual(store.service_key, "environment-secret-test")

    def test_rpc_errors_do_not_expose_provider_body(self):
        import io
        import urllib.error
        error = urllib.error.HTTPError(
            "https://project.supabase.co/rest/v1/rpc/secret",
            500, "failure", {}, io.BytesIO(b'{"message":"private-key-or-user-data"}')
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(SupabaseStoreError) as caught:
                self.store.login_attempt()
        self.assertNotIn("private-key", str(caught.exception))
        self.assertNotIn("user-data", str(caught.exception))

    def test_expected_quota_rejections_are_usage_limits(self):
        import io
        import urllib.error

        cases = (
            ("NESIL_DAILY_LIMIT", "reserve"),
            ("NESIL_MINUTE_LIMIT", "reserve"),
            ("NESIL_PROVIDER_COOLDOWN", "reserve"),
            ("NESIL_LOGIN_LIMIT", "login_attempt"),
        )
        for code, operation_name in cases:
            with self.subTest(code=code):
                error = urllib.error.HTTPError(
                    "https://project.supabase.co/rest/v1/rpc/private",
                    400, "quota", {}, io.BytesIO(json.dumps({"message": code}).encode()),
                )
                with patch("urllib.request.urlopen", side_effect=error):
                    with self.assertRaises(SupabaseUsageLimit):
                        operation = getattr(self.store, operation_name)
                        operation("user-hash", 100) if operation_name == "reserve" else operation()

    def test_invalid_reservation_is_not_misreported_as_quota_exhaustion(self):
        import io
        import urllib.error

        error = urllib.error.HTTPError(
            "https://project.supabase.co/rest/v1/rpc/private",
            400, "invalid", {}, io.BytesIO(b'{"message":"NESIL_INVALID_RESERVATION"}'),
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(SupabaseStoreError) as caught:
                self.store.reserve("user-hash", 100)
        self.assertNotIsInstance(caught.exception, SupabaseUsageLimit)


if __name__ == "__main__":
    unittest.main()
