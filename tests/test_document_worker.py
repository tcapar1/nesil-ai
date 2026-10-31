import unittest
from unittest.mock import patch

from document_worker import load_saved_documents
from file_reader import FileResult


class FakeStore:
    def __init__(self, files):
        self.files = files
        self.calls = []

    def download(self, path):
        self.calls.append(path)
        value = self.files[path]
        if isinstance(value, Exception):
            raise value
        return value


class SavedDocumentBatchTests(unittest.TestCase):
    @patch("document_worker.extract_bounded")
    def test_loads_saved_documents_and_respects_order(self, extract):
        extract.side_effect = lambda upload: FileResult(upload.name, "metin", "okundu")
        store = FakeStore({"u/a.pdf": b"pdf", "u/b.txt": b"hello"})
        rows = [
            {"file_name": "a.pdf", "object_path": "u/a.pdf", "file_size": 3},
            {"file_name": "b.txt", "object_path": "u/b.txt", "file_size": 5},
        ]
        loaded, skipped = load_saved_documents(store, rows)
        self.assertEqual([item.name for item in loaded], ["a.pdf", "b.txt"])
        self.assertEqual(skipped, [])
        self.assertEqual(store.calls, ["u/a.pdf", "u/b.txt"])

    @patch("document_worker.extract_bounded")
    def test_batch_is_limited_by_file_count_and_total_downloaded_bytes(self, extract):
        extract.side_effect = lambda upload: FileResult(upload.name, "metin", "okundu")
        store = FakeStore({"u/a.txt": b"123", "u/b.txt": b"456", "u/c.txt": b"789"})
        rows = [{"file_name": f"{name}.txt", "object_path": f"u/{name}.txt"} for name in "abc"]
        loaded, skipped = load_saved_documents(store, rows, max_files=2, max_total_bytes=5)
        self.assertEqual([item.name for item in loaded], ["a.txt"])
        self.assertEqual(len(skipped), 2)
        self.assertIn("Toplam", skipped[0][1])
        self.assertIn("2 belge", skipped[1][1])

    @patch("document_worker.extract_bounded")
    def test_duplicate_names_are_not_loaded_twice(self, extract):
        extract.side_effect = lambda upload: FileResult(upload.name, "metin", "okundu")
        store = FakeStore({"u/a.txt": b"one", "u/b.txt": b"two"})
        rows = [
            {"file_name": "same.txt", "object_path": "u/a.txt"},
            {"file_name": "same.txt", "object_path": "u/b.txt"},
        ]
        loaded, skipped = load_saved_documents(store, rows)
        self.assertEqual(len(loaded), 1)
        self.assertIn("zaten seçildi", skipped[0][1])

    @patch("document_worker.extract_bounded")
    def test_download_errors_and_unreadable_documents_are_reported(self, extract):
        extract.side_effect = [FileResult("bad.pdf", scope="Okunabilir metin bulunamadı."), FileResult("ok.txt", "text", "okundu")]
        store = FakeStore({"u/bad.pdf": b"bad", "u/ok.txt": b"ok", "u/offline.txt": OSError("private")})
        rows = [
            {"file_name": "bad.pdf", "object_path": "u/bad.pdf"},
            {"file_name": "ok.txt", "object_path": "u/ok.txt"},
            {"file_name": "offline.txt", "object_path": "u/offline.txt"},
        ]
        loaded, skipped = load_saved_documents(store, rows)
        self.assertEqual([item.name for item in loaded], ["ok.txt"])
        self.assertEqual(len(skipped), 2)
        self.assertNotIn("private", str(skipped))


if __name__ == "__main__":
    unittest.main()
