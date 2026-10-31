import json
import unittest
from unittest.mock import patch

from supabase_files import SupabaseFileStore, SupabaseFileError


class FakeResponse:
    def __init__(self, body=b"{}"):
        self.body = body
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit=-1): return self.body[:limit]


class SupabaseFileTests(unittest.TestCase):
    def setUp(self):
        self.store = SupabaseFileStore(
            "https://project.supabase.co", "publishable", "user-jwt", "user-123"
        )

    def test_upload_uses_user_folder_and_never_overwrites(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b'{"Key":"ok"}')) as opener:
            result = self.store.upload("../rapor.pdf", b"%PDF-test")
        request = opener.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertIn("/nesil-user-files/user-123/", request.full_url)
        self.assertEqual(request.data, b"%PDF-test")
        self.assertTrue(result["path"].startswith("user-123/"))
        self.assertEqual(result["name"], "rapor.pdf")

    def test_upload_rejects_unsupported_and_oversized_files(self):
        with self.assertRaises(SupabaseFileError):
            self.store.upload("script.exe", b"x")
        with self.assertRaises(SupabaseFileError):
            self.store.upload("large.pdf", b"x" * (10 * 1024 * 1024 + 1))

    def test_list_returns_only_object_rows_with_user_scoped_paths(self):
        body = json.dumps([{"name": "abc_rapor.pdf", "id": "object-id", "metadata": {"size": 9}}]).encode()
        with patch("urllib.request.urlopen", return_value=FakeResponse(body)) as opener:
            rows = self.store.list_files()
        request = opener.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertIn("/object/list/nesil-user-files", request.full_url)
        self.assertEqual(rows[0]["name"], "rapor.pdf")
        self.assertEqual(rows[0]["path"], "user-123/abc_rapor.pdf")

    def test_download_and_delete_reject_other_users_paths(self):
        with self.assertRaises(SupabaseFileError):
            self.store.download("another-user/private.pdf")
        with self.assertRaises(SupabaseFileError):
            self.store.delete("user-123/../other-user/private.pdf")

    def test_delete_uses_storage_remove_post_endpoint(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"[]")) as opener:
            self.store.delete("user-123/abc_rapor.pdf")
        request = opener.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertTrue(request.full_url.endswith("/storage/v1/object/nesil-user-files"))
        self.assertEqual(json.loads(request.data), {"prefixes": ["user-123/abc_rapor.pdf"]})
        self.assertEqual(request.get_header("Authorization"), "Bearer user-jwt")


if __name__ == "__main__":
    unittest.main()
