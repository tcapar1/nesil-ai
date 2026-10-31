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

    def test_touch_conversation_updates_activity_timestamp(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"")) as opener:
            self.store.touch_conversation("conversation-1")
        req = opener.call_args.args[0]
        self.assertEqual(req.get_method(), "PATCH")
        self.assertIn("id=eq.conversation-1", req.full_url)
        payload = json.loads(req.data)
        self.assertIn("updated_at", payload)
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")

    def test_touch_conversation_rejects_invalid_id(self):
        with self.assertRaises(SupabaseDataError):
            self.store.touch_conversation("")

    def test_list_conversations_excludes_archived_by_default_and_sorts_pins_first(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"[]")) as opener:
            self.store.list_conversations()
        req = opener.call_args.args[0]
        self.assertIn("is_archived=eq.false", req.full_url)
        self.assertIn("is_pinned.desc", req.full_url)
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")

    def test_list_conversations_can_include_archived(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"[]")) as opener:
            self.store.list_conversations(include_archived=True)
        self.assertNotIn("is_archived=eq.false", opener.call_args.args[0].full_url)

    def test_pin_and_archive_update_only_allowed_flags(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"")) as opener:
            self.store.pin_conversation("conversation-1", True)
        req = opener.call_args.args[0]
        self.assertEqual(req.get_method(), "PATCH")
        self.assertEqual(json.loads(req.data)["is_pinned"], True)
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"")) as opener:
            self.store.archive_conversation("conversation-1", True)
        self.assertEqual(json.loads(opener.call_args.args[0].data)["is_archived"], True)

    def test_conversation_flag_rejects_invalid_flag_and_id(self):
        with self.assertRaises(SupabaseDataError):
            self.store.set_conversation_flag("conversation-1", "user_id", True)
        with self.assertRaises(SupabaseDataError):
            self.store.pin_conversation("", True)

    def test_update_conversation_title_is_validated_and_user_scoped(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"")) as opener:
            self.store.update_conversation_title("conversation-1", "Yeni başlık")
        req = opener.call_args.args[0]
        self.assertEqual(req.get_method(), "PATCH")
        self.assertIn("id=eq.conversation-1", req.full_url)
        self.assertEqual(json.loads(req.data)["title"], "Yeni başlık")
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")

    def test_update_conversation_title_rejects_invalid_values(self):
        with self.assertRaises(SupabaseDataError):
            self.store.update_conversation_title("", "Başlık")
        with self.assertRaises(SupabaseDataError):
            self.store.update_conversation_title("conversation-1", "x" * 121)

    def test_list_documents_filters_by_name_and_folder_with_user_jwt(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"[]")) as opener:
            self.store.list_documents(search="budget", folder="Finance")
        req = opener.call_args.args[0]
        self.assertIn("file_name=ilike", req.full_url)
        self.assertIn("folder_name=eq.Finance", req.full_url)
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")

    def test_add_document_uses_current_user_and_private_object_path(self):
        body = json.dumps([{"id":"doc-1","file_name":"report.pdf"}]).encode()
        with patch("urllib.request.urlopen", return_value=FakeResponse(body)) as opener:
            row = self.store.add_document("user-1/abc_report.pdf", "report.pdf", 1024, "application/pdf")
        req = opener.call_args.args[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(json.loads(req.data)["user_id"], "user-1")
        self.assertEqual(json.loads(req.data)["object_path"], "user-1/abc_report.pdf")
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")
        self.assertEqual(row["id"], "doc-1")

    def test_begin_upload_and_finish_use_user_jwt_rpc(self):
        response = FakeResponse(b'{"operation_id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa","state":"pending"}')
        with patch("urllib.request.urlopen", return_value=response) as opener:
            result = self.store.begin_document_upload("a" * 32, "user-1/a_report.pdf", "report.pdf", 10,
                                                     "application/pdf", "b" * 64)
        request = opener.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/rest/v1/rpc/nesil_begin_document_upload"))
        self.assertEqual(request.get_header("Authorization"), "Bearer user-jwt")
        self.assertEqual(json.loads(request.data)["p_sha256"], "b" * 64)
        self.assertEqual(result["state"], "pending")

    def test_pending_document_operations_are_owner_scoped_and_bounded(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"[]")) as opener:
            self.store.list_pending_document_operations(limit=1000)
        request = opener.call_args.args[0]
        self.assertIn("nesil_document_operations", request.full_url)
        self.assertIn("state=eq.pending", request.full_url)
        self.assertIn("limit=100", request.full_url)
        self.assertEqual(request.get_header("Authorization"), "Bearer user-jwt")

    def test_begin_upload_rejects_path_digest_and_operation_before_network(self):
        with patch("urllib.request.urlopen") as opener:
            for args in (("a" * 32, "other-user/x.pdf", "x.pdf", 10, "application/pdf", "b" * 64),
                         ("bad", "user-1/x.pdf", "x.pdf", 10, "application/pdf", "b" * 64),
                         ("a" * 32, "user-1/x.pdf", "x.pdf", 10, "application/pdf", "short")):
                with self.assertRaises(SupabaseDataError):
                    self.store.begin_document_upload(*args)
        opener.assert_not_called()

    def test_add_document_retry_returns_existing_row_without_overwriting_metadata(self):
        existing = [{"id": "doc-1", "object_path": "user-1/op_report.pdf", "file_name": "renamed.pdf", "tags": ["important"]}]
        with patch("urllib.request.urlopen", side_effect=[FakeResponse(b"[]"), FakeResponse(json.dumps(existing).encode())]) as opener:
            row = self.store.add_document("user-1/op_report.pdf", "report.pdf", 1024, "application/pdf")
        self.assertEqual(row["file_name"], "renamed.pdf")
        self.assertEqual(row["tags"], ["important"])
        self.assertEqual(opener.call_count, 2)
        self.assertIn("on_conflict=object_path", opener.call_args_list[0].args[0].full_url)
        self.assertEqual(opener.call_args_list[0].args[0].get_header("Prefer"), "resolution=ignore-duplicates,return=representation")

    def test_rename_document_keeps_extension_and_rejects_path_or_extension_change(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"")) as opener:
            self.store.rename_document("doc-1", "report.pdf", "new report.pdf")
        request = opener.call_args.args[0]
        self.assertEqual(request.get_method(), "PATCH")
        self.assertEqual(json.loads(request.data)["file_name"], "new report.pdf")
        with self.assertRaises(SupabaseDataError):
            self.store.rename_document("doc-1", "report.pdf", "report.docx")
        with self.assertRaises(SupabaseDataError):
            self.store.rename_document("doc-1", "report.pdf", "../report.pdf")

    def test_add_document_rejects_foreign_path_and_oversized_file(self):
        with self.assertRaises(SupabaseDataError):
            self.store.add_document("other-user/file.pdf", "file.pdf", 100, "application/pdf")
        with self.assertRaises(SupabaseDataError):
            self.store.add_document("user-1/file.pdf", "file.pdf", 11 * 1024 * 1024, "application/pdf")

    def test_update_document_organization_validates_and_updates_selected_record(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"")) as opener:
            self.store.update_document_organization("doc-1", "Projeler", ["2026", "Rapor"])
        req = opener.call_args.args[0]
        self.assertEqual(req.get_method(), "PATCH")
        self.assertIn("id=eq.doc-1", req.full_url)
        self.assertEqual(json.loads(req.data)["folder_name"], "Projeler")
        self.assertEqual(json.loads(req.data)["tags"], ["2026", "Rapor"])
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")

    def test_update_document_organization_rejects_bad_tags(self):
        with self.assertRaises(SupabaseDataError):
            self.store.update_document_organization("doc-1", "Projeler", ["x" * 31])
        with self.assertRaises(SupabaseDataError):
            self.store.update_document_organization("doc-1", " ", [])

    def test_delete_document_uses_id_filter_and_user_jwt(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"")) as opener:
            self.store.delete_document("doc-1")
        req = opener.call_args.args[0]
        self.assertEqual(req.get_method(), "DELETE")
        self.assertIn("id=eq.doc-1", req.full_url)
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")

    def test_update_memory_patches_only_selected_memory(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"")) as opener:
            self.store.update_memory("memory-1", "Yeni bilgi")
        req = opener.call_args.args[0]
        self.assertEqual(req.get_method(), "PATCH")
        self.assertIn("id=eq.memory-1", req.full_url)
        self.assertEqual(json.loads(req.data)["memory_text"], "Yeni bilgi")
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")

    def test_update_memory_rejects_empty_and_oversized_text(self):
        with self.assertRaises(SupabaseDataError):
            self.store.update_memory("memory-1", " ")
        with self.assertRaises(SupabaseDataError):
            self.store.update_memory("memory-1", "x" * 4001)

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

    def test_add_messages_writes_both_turns_in_one_request(self):
        messages = [
            {"role": "user", "content": "Merhaba"},
            {"role": "assistant", "content": "Merhaba!"},
        ]
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"")) as opener:
            self.store.add_messages("conv-1", messages)
        self.assertEqual(opener.call_count, 1)
        req = opener.call_args.args[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(json.loads(req.data), [
            {"conversation_id": "conv-1", **message} for message in messages
        ])
        self.assertEqual(req.get_header("Authorization"), "Bearer user-jwt")
        self.assertEqual(req.get_header("Prefer"), "return=minimal")

    def test_add_messages_rejects_invalid_batch_before_network(self):
        with patch("urllib.request.urlopen") as opener:
            with self.assertRaises(SupabaseDataError):
                self.store.add_messages("conv-1", [
                    {"role": "user", "content": "Soru"},
                    {"role": "system", "content": "geçersiz"},
                ])
        opener.assert_not_called()

    def test_add_messages_rejects_oversized_batch_before_network(self):
        with patch("urllib.request.urlopen") as opener:
            with self.assertRaises(SupabaseDataError):
                self.store.add_messages("conv-1", [
                    {"role": "user", "content": "x" * 50000} for _ in range(20)
                ])
        opener.assert_not_called()

    def test_list_messages_uses_id_as_stable_tiebreaker(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"[]")) as opener:
            self.store.list_messages("conv-1")
        self.assertIn("order=created_at.asc%2Cid.asc", opener.call_args.args[0].full_url)

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
