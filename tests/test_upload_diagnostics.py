import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from openpyxl import Workbook
from file_reader import extract_file
from supabase_files import SupabaseFileStore, SupabaseFileError


class Upload:
    def __init__(self, name, raw):
        self.name = name
        self.raw = raw
        self.size = len(raw)

    def getvalue(self):
        return self.raw


class UploadDiagnosticsTests(unittest.TestCase):
    def test_xlsx_extracts_sheet_and_cell_values(self):
        buffer = io.BytesIO()
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Cevap Anahtarı"
        sheet.append(["Soru", "Cevap"])
        sheet.append([1, "A"])
        workbook.save(buffer)
        workbook.close()

        result = extract_file(Upload("cevap.xlsx", buffer.getvalue()))

        self.assertIn("Cevap Anahtarı", result.text)
        self.assertIn("A2=1", result.text)
        self.assertIn("B2=A", result.text)
        self.assertNotEqual(result.status, "okunamadı")

    def test_storage_error_exposes_http_status_and_safe_message(self):
        store = SupabaseFileStore(
            "https://project.supabase.co", "publishable", "user-jwt", "user-123"
        )
        error = urllib.error.HTTPError(
            "https://project.supabase.co/storage", 400, "Bad Request", {},
            io.BytesIO(json.dumps({"message": "mime type not supported"}).encode()),
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(SupabaseFileError) as caught:
                store.upload("cevap.xlsx", b"test")

        self.assertIn("HTTP 400", str(caught.exception))
        self.assertIn("mime type not supported", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
