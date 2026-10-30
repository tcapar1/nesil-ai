import json
import unittest
from unittest.mock import patch

from supabase_auth import SupabaseAuthClient, SupabaseAuthError, create_auth_client


class FakeResponse:
    def __init__(self, body):
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, limit=-1):
        return self.body[:limit]


class SupabaseAuthTests(unittest.TestCase):
    def setUp(self):
        self.client = SupabaseAuthClient("https://project.supabase.co", "public-test-key")

    def test_password_login_uses_public_key_and_returns_tokens(self):
        payload = {"access_token": "access", "refresh_token": "refresh", "user": {"id": "user-1"}}
        with patch("urllib.request.urlopen", return_value=FakeResponse(json.dumps(payload).encode())) as opener:
            result = self.client.sign_in("user@example.com", "long-password")
        request = opener.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/auth/v1/token?grant_type=password"))
        self.assertEqual(request.get_header("Apikey"), "public-test-key")
        self.assertEqual(result["access_token"], "access")

    def test_signup_endpoint(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b'{"user":{"id":"user-1"}}')) as opener:
            self.client.sign_up("user@example.com", "long-password")
        self.assertTrue(opener.call_args.args[0].full_url.endswith("/auth/v1/signup"))

    def test_refresh_rotates_tokens(self):
        payload = {"access_token": "new-access", "refresh_token": "new-refresh"}
        with patch("urllib.request.urlopen", return_value=FakeResponse(json.dumps(payload).encode())):
            result = self.client.refresh("old-refresh")
        self.assertEqual(result["refresh_token"], "new-refresh")

    def test_logout_sends_user_access_token(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"{}")) as opener:
            self.client.sign_out("user-access")
        request = opener.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/auth/v1/logout"))
        self.assertEqual(request.get_header("Authorization"), "Bearer user-access")

    def test_missing_public_key_fails_closed(self):
        with self.assertRaises(SupabaseAuthError):
            SupabaseAuthClient("https://project.supabase.co", "")

    def test_secrets_accept_anon_and_publishable_aliases(self):
        anon = create_auth_client({"SUPABASE_URL": "https://project.supabase.co", "SUPABASE_ANON_KEY": "anon"})
        pub = create_auth_client({"SUPABASE_URL": "https://project.supabase.co", "SUPABASE_PUBLISHABLE_KEY": "publishable"})
        self.assertEqual(anon.anon_key, "anon")
        self.assertEqual(pub.anon_key, "publishable")


if __name__ == "__main__":
    unittest.main()
