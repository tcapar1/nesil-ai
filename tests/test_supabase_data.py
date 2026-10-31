import json
import unittest
from unittest.mock import patch
from supabase_data import SupabaseDataStore, SupabaseDataError, create_data_store


class FakeResponse:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit=-1): return self.body[:limit]


class SupabaseDataTests(unittest.TestCase):
    def setUp(self):
        self.store = SupabaseDataStore("https://project.supabase.co", "public-key", "user-jwt", "user-1")

    def test_factory_prefers_publishable_key_and_falls_back_to_anon(self):
        secrets = {
            "SUPABASE_URL": "https://project.supabase.co",
            "SUPABASE_PUBLISHABLE_KEY": "publishable-key",
            "SUPABASE_ANON_KEY": "legacy-anon-key",
        }
        store = create_data_store(secrets, "user-jwt", "user-1")
        self.assertEqual(store.anon_key, "publishable-key")
        fallback = create_data_store(
            {"SUPABASE_URL": "https://project.supabase.co", "SUPABASE_ANON_KEY": "legacy-anon-key"},
            "user-jwt", "user-1",
        )
        self.assertEqual(fallback.anon_key, "legacy-anon-key")

    def test_list_conversations_uses_user_jwt_not_service_role(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"[]")) as opener:
            self.store.list_conversations()
        req = opener.call_args.args[0]
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")
        self.assertEqual(req.get_header("Apikey"), "public-key")
        self.assertIn("nesil_conversations", req.full_url)

    def test_add_message_payload(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b'[{"id":1}]')) as opener:
            self.store.add_message("conv-1", "user", "Merhaba")
        req = opener.call_args.args[0]
        body = json.loads(req.data)
        self.assertEqual(body, {"conversation_id":"conv-1","role":"user","content":"Merhaba"})

    def test_add_memory_rejects_empty_and_oversized(self):
        with self.assertRaises(SupabaseDataError): self.store.add_memory("")
        with self.assertRaises(SupabaseDataError): self.store.add_memory("x" * 4001)

    def test_invalid_role_rejected(self):
        with self.assertRaises(SupabaseDataError):
            self.store.add_message("conv-1", "system", "no")

    def test_401_reports_expired_session_without_response_body(self):
        import io, urllib.error
        err = urllib.error.HTTPError("https://project.supabase.co/rest/v1/x", 401, "bad", {}, io.BytesIO(b"private"))
        with patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(SupabaseDataError) as caught:
                self.store.list_conversations()
        self.assertNotIn("private", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
