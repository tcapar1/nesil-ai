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

    def test_get_profile_is_scoped_to_authenticated_user(self):
        body = json.dumps([{"user_id": "user-1", "display_name": "Test"}]).encode()
        with patch("urllib.request.urlopen", return_value=FakeResponse(body)) as opener:
            row = self.store.get_profile()
        req = opener.call_args.args[0]
        self.assertIn("user_id=eq.user-1", req.full_url)
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")
        self.assertEqual(row["display_name"], "Test")

    def test_update_profile_sends_only_display_name_for_current_user(self):
        body = json.dumps([{"user_id": "user-1", "display_name": "Yeni Ad"}]).encode()
        with patch("urllib.request.urlopen", return_value=FakeResponse(body)) as opener:
            row = self.store.update_profile("Yeni Ad")
        req = opener.call_args.args[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertIn("on_conflict=user_id", req.full_url)
        self.assertEqual(req.get_header("Prefer"), "resolution=merge-duplicates,return=representation")
        self.assertEqual(json.loads(req.data), {"user_id": "user-1", "display_name": "Yeni Ad"})
        self.assertEqual(row["display_name"], "Yeni Ad")

    def test_update_profile_upserts_profile_for_existing_user(self):
        body = json.dumps([{"user_id": "user-1", "display_name": "Eski Hesap"}]).encode()
        with patch("urllib.request.urlopen", return_value=FakeResponse(body)) as opener:
            row = self.store.update_profile("Eski Hesap")
        req = opener.call_args.args[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertIn("on_conflict=user_id", req.full_url)
        self.assertEqual(req.get_header("Prefer"), "resolution=merge-duplicates,return=representation")
        self.assertEqual(json.loads(req.data), {"user_id": "user-1", "display_name": "Eski Hesap"})
        self.assertEqual(row["display_name"], "Eski Hesap")

    def test_update_profile_rejects_overlong_name(self):
        with self.assertRaises(SupabaseDataError):
            self.store.update_profile("x" * 81)

    def test_list_conversations_uses_user_jwt_not_service_role(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"[]")) as opener:
            self.store.list_conversations()
        req = opener.call_args.args[0]
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")
        self.assertEqual(req.get_header("Apikey"), "public-key")
        self.assertIn("nesil_conversations", req.full_url)

    def test_delete_conversation_uses_id_filter_and_delete_method(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"")) as opener:
            self.store.delete_conversation("conversation-1")
        req = opener.call_args.args[0]
        self.assertEqual(req.get_method(), "DELETE")
        self.assertIn("id=eq.conversation-1", req.full_url)
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")

    def test_delete_conversation_rejects_empty_id(self):
        with self.assertRaises(SupabaseDataError):
            self.store.delete_conversation("")

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
