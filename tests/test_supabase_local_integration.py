"""Real JWT/RLS exercise against an ephemeral local Supabase stack in CI."""
import os
import unittest
import uuid

from supabase_auth import SupabaseAuthClient
from supabase_data import SupabaseDataStore
from supabase_files import SupabaseFileError, SupabaseFileStore


@unittest.skipUnless(os.environ.get("NESIL_LOCAL_SUPABASE_TEST") == "1", "requires disposable local Supabase stack")
class LocalSupabaseAuthRlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = os.environ["API_URL"]
        cls.key = os.environ["ANON_KEY"]
        cls.auth = SupabaseAuthClient(cls.url, cls.key)

    def test_two_real_auth_sessions_isolate_chat_memory_and_private_files(self):
        suffix = uuid.uuid4().hex
        sessions = []
        try:
            for label in ("a", "b"):
                email = f"nesil-{label}-{suffix}@example.com"
                password = "Local-test-Only-42!"
                self.auth.sign_up(email, password)
                session = self.auth.sign_in(email, password)
                sessions.append(session)
            a, b = sessions
            user_a = a["user"]["id"]
            user_b = b["user"]["id"]
            store_a = SupabaseDataStore(self.url, self.key, a["access_token"], user_a)
            store_b = SupabaseDataStore(self.url, self.key, b["access_token"], user_b)

            conversation = store_a.create_conversation("A private test conversation")
            store_a.add_messages(conversation["id"], [
                {"role": "user", "content": "private-local-test"},
                {"role": "assistant", "content": "private-local-answer"},
            ])
            memory = store_a.add_memory("private-local-memory")
            self.assertEqual(store_a.list_messages(conversation["id"])[0]["content"], "private-local-test")
            self.assertEqual(store_b.list_conversations(), [])
            self.assertEqual(store_b.list_memory(), [])
            self.assertEqual(store_b.list_messages(conversation["id"]), [])
            store_b.delete_memory(memory["id"])
            self.assertEqual(store_a.list_memory()[0]["memory_text"], "private-local-memory")

            files_a = SupabaseFileStore(self.url, self.key, a["access_token"], user_a)
            files_b = SupabaseFileStore(self.url, self.key, b["access_token"], user_b)
            operation_id = uuid.uuid4().hex
            raw = b"synthetic local Supabase integration fixture"
            description = files_a.describe_upload("fixture.txt", raw, operation_id)
            store_a.begin_document_upload(operation_id, description["path"], description["name"],
                                          description["size"], description["content_type"], description["sha256"])
            files_a.upload("fixture.txt", raw, operation_id)
            store_a.finish_document_upload(operation_id)
            self.assertEqual(len(store_a.list_documents()), 1)
            self.assertEqual(store_b.list_documents(), [])
            with self.assertRaises(SupabaseFileError):
                files_b.download(description["path"])

            doc = store_a.list_documents()[0]
            delete_id = uuid.uuid4().hex
            store_a.begin_document_delete(delete_id, doc["id"])
            files_a.delete(description["path"])
            store_a.finish_document_delete(delete_id)
            self.assertEqual(store_a.list_documents(), [])
        finally:
            for session in sessions:
                try:
                    self.auth.sign_out(session["access_token"])
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
