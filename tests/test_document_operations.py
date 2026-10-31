import hashlib
import unittest
from unittest.mock import Mock

from document_operations import delete_document, recover_delete, recover_upload, save_document


class DocumentOperationTests(unittest.TestCase):
    def test_upload_failure_keeps_ledger_pending_and_matching_retry_finishes(self):
        files, data = Mock(), Mock()
        raw = b"synthetic file bytes"
        digest = hashlib.sha256(raw).hexdigest()
        files.describe_upload.return_value = {
            "path": "user/op" + digest + "_doc.txt", "name": "doc.txt", "size": len(raw),
            "content_type": "text/plain", "sha256": digest,
        }
        files.upload.side_effect = [OSError("simulated Storage outage"), {"path": "object"}]
        with self.assertRaises(OSError):
            save_document(files, data, "doc.txt", raw, "a" * 32)
        data.begin_document_upload.assert_called_once()
        data.finish_document_upload.assert_not_called()

        operation = {"operation_id": "a" * 32, "file_name": "doc.txt", "file_size": len(raw), "sha256": digest}
        with self.assertRaisesRegex(ValueError, "aynı dosya"):
            recover_upload(files, data, operation, "doc.txt", b"different contents")
        files.upload.assert_called_once()
        recover_upload(files, data, operation, "doc.txt", raw)
        self.assertEqual(files.upload.call_count, 2)
        data.finish_document_upload.assert_called_once_with("a" * 32)

    def test_delete_failure_leaves_metadata_finalization_for_retry(self):
        files, data = Mock(), Mock()
        files.delete.side_effect = [OSError("simulated Storage outage"), None]
        with self.assertRaises(OSError):
            delete_document(files, data, "b" * 32, "doc-1", "user/doc.pdf")
        data.begin_document_delete.assert_called_once_with("b" * 32, "doc-1")
        data.finish_document_delete.assert_not_called()
        recover_delete(files, data, {"operation_id": "b" * 32, "object_path": "user/doc.pdf"})
        data.finish_document_delete.assert_called_once_with("b" * 32)


if __name__ == "__main__":
    unittest.main()
