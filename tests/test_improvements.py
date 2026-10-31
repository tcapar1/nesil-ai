import io
import json
import tempfile
import unittest
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

from model_client import ask_model, wants_research, build_messages, MAX_INPUT_BYTES
from research import research_record, enrich_sources, render_citations
from file_reader import extract_file, select_context
from usage_limits import UsageStore, UsageLimit
from access_control import authenticate, configured_users
from app_service import call_with_limits


class Upload:
    def __init__(self, name, raw):
        self.name, self.raw, self.size = name, raw, len(raw)
    def getvalue(self):
        return self.raw


class ImprovementsTests(unittest.TestCase):
    def test_smalltalk_does_not_force_search(self):
        for question in ("Merhaba", "nesil ai hazırmısın yenimahalle çözüm kursta işe başlamaya", "Hazır mısın?", "Teşekkürler!"):
            self.assertFalse(wants_research(question, True))
            def fake(request, **kwargs):
                payload = json.loads(request.data)
                self.assertNotIn("tools", payload)
                self.assertEqual(payload["tool_choice"], "none")
                return io.BytesIO(json.dumps({"choices": [{"message": {"content": "Hazırım!"}}]}).encode())
            result = ask_model(question, "Genel", [], web_enabled=True, api_key="fake", opener=fake)
            self.assertTrue(result.ok)
            self.assertFalse(result.research["requested"])
        self.assertTrue(wants_research("Yenimahalle Çözüm Kurs adresini araştır", True))

    def test_error_category_is_useful_and_private(self):
        body = {"error": {"code": "tool_use_failed", "message": "private prompt API-secret"}}
        def fail(*a, **k):
            raise urllib.error.HTTPError("https://example.invalid", 400, "error", {}, io.BytesIO(json.dumps(body).encode()))
        with self.assertLogs("nesil.model", level="WARNING") as logs:
            result = ask_model("test", "Genel", [], api_key="fake", opener=fail)
        self.assertIn("Araştırma aracı", result.text)
        self.assertNotIn("kısa", result.text)
        self.assertEqual(len(result.error_id), 12)
        self.assertIn("tool_use_failed", str(logs.output))
        self.assertNotIn("private", str(logs.output) + result.text)

    def test_no_source_cannot_publish_specific_address(self):
        def fake(*a, **k):
            return io.BytesIO(json.dumps({"choices": [{"message": {"content": "Adres: Uydurma sokak 99【1†L1-L4】"}}]}).encode())
        result = ask_model("Adresini ver", "Genel", [], web_enabled=True, api_key="fake", opener=fake)
        self.assertNotIn("Uydurma", result.text)
        self.assertEqual(result.research["status"], "no_sources")
        self.assertEqual(result.research["unresolved_citations"], 1)

    def test_explicit_provider_citation_mapping(self):
        record = research_record("Cevap【7†L1-L4】〖9†L3-L8〗", True, "now")
        tools = [{"output": json.dumps({"sources": [{"id": "7", "url": "https://example.org/course", "title": "Kurs", "snippet": "Adres metni"}]})}]
        enrich_sources(record, tools, [])
        answer = render_citations("Cevap【7†L1-L4】〖9†L3-L8〗", record)
        self.assertIn("[Kaynak](https://example.org/course)", answer)
        self.assertIn("eşleştirilemedi", answer)
        self.assertFalse(record["sources"][0]["verified"])
        self.assertEqual(record["unresolved_citations"], 1)

    def test_citation_ids_are_not_guessed_from_order(self):
        record = research_record("", True, "now")
        enrich_sources(record, [{"url": "https://example.org/"}], [])
        self.assertIn("eşleştirilemedi", render_citations("【1†L1】", record))

    def test_document_tail_is_indexed_and_located(self):
        raw = ("Genel bilgiler.\n" * 2500 + "\nSözleşmenin fesih bedeli 98765 TL.").encode()
        result = extract_file(Upload("sozlesme.txt", raw))
        context = select_context([result], "fesih bedeli nedir")
        self.assertIn("98765", context)
        self.assertIn("karakter", context)

    def test_pdf_late_page_and_page_marker(self):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject
        writer = PdfWriter()
        for i in range(40):
            page = writer.add_blank_page(width=300, height=300)
            if i == 39:
                font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
                page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
                stream = DecodedStreamObject()
                stream.set_data(b"BT /F1 12 Tf 10 10 Td (fesih 98765 TL) Tj ET")
                page[NameObject("/Contents")] = writer._add_object(stream)
        raw = io.BytesIO()
        writer.write(raw)
        result = extract_file(Upload("uzun.pdf", raw.getvalue()))
        context = select_context([result], "fesih")
        self.assertIn("98765", context)
        self.assertIn("Sayfa 40", context)

    def test_excel_late_rows_include_cell_address(self):
        from openpyxl import Workbook
        wb = Workbook()
        wb.active.cell(600, 2, "Fesih bedeli 98765 TL")
        raw = io.BytesIO()
        wb.save(raw)
        wb.close()
        result = extract_file(Upload("uzun.xlsx", raw.getvalue()))
        self.assertIn("B600=Fesih", select_context([result], "fesih"))

    def test_ocr_is_opt_in_and_labels_its_page(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=300)
        raw = io.BytesIO()
        writer.write(raw)
        upload = Upload("tarama.pdf", raw.getvalue())
        with patch("ocr_reader.ocr_page", return_value="Taranan fesih bedeli 123 TL") as ocr:
            self.assertFalse(extract_file(upload).text)
            ocr.assert_not_called()
            result = extract_file(upload, ocr=True)
            self.assertIn("Sayfa 1 OCR", result.text)
            self.assertIn("123", result.text)

    def test_ocr_unavailable_is_explicit(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=300)
        raw = io.BytesIO()
        writer.write(raw)
        with patch("ocr_reader.ocr_page", side_effect=ImportError("private details")):
            result = extract_file(Upload("tarama.pdf", raw.getvalue()), ocr=True)
        self.assertIn("OCR kullanılamadı", result.scope)
        self.assertNotIn("private", result.scope)

    def test_bounded_document_worker_reads_text(self):
        from document_worker import extract_bounded
        result = extract_bounded(Upload("test.txt", "Merhaba dünya".encode()))
        self.assertIn("Merhaba", result.text)

    def test_document_worker_timeout_terminates_child(self):
        from document_worker import extract_bounded
        process, context, receiver, sender = Mock(), Mock(), Mock(), Mock()
        context.Pipe.return_value = (receiver, sender)
        context.Process.return_value = process
        receiver.poll.return_value = False
        process.pid = 123
        process.is_alive.side_effect = [True, False, False]
        with patch("document_worker.multiprocessing.get_context", return_value=context):
            result = extract_bounded(Upload("slow.pdf", b"test"), timeout=0.01)
        self.assertIn("süre sınırını", result.scope)
        process.terminate.assert_called_once()
        receiver.close.assert_called_once()

    def test_worker_cleanup_does_not_mask_timeout_if_os_is_slow(self):
        from document_worker import extract_bounded
        process, context, receiver, sender = Mock(), Mock(), Mock(), Mock()
        context.Pipe.return_value = (receiver, sender)
        context.Process.return_value = process
        receiver.poll.return_value = False
        process.pid = 123
        process.is_alive.return_value = True
        with patch("document_worker.multiprocessing.get_context", return_value=context):
            result = extract_bounded(Upload("slow.pdf", b"test"), timeout=0.01)
        self.assertIn("süre sınırını", result.scope)
        process.kill.assert_called_once()
        process.close.assert_not_called()

    def test_access_configuration_and_authentication(self):
        users = configured_users({"NESIL_USERS": {"ayse": "example-long-code-123"}})
        self.assertTrue(authenticate(users, "ayse", "example-long-code-123"))
        self.assertFalse(authenticate(users, "ayse", "wrong"))
        self.assertFalse(authenticate(users, "unknown", "example-long-code-123"))
        with self.assertRaises(ValueError):
            configured_users({"NESIL_USERS": {"ayse": "short"}})

    def test_global_budget_survives_new_store_and_concurrent_users(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usage.db"
            store = UsageStore(path)
            def reserve(i):
                try:
                    store.reserve(str(i), 10, daily_requests=3)
                    return True
                except UsageLimit:
                    return False
            with ThreadPoolExecutor(max_workers=8) as executor:
                self.assertEqual(sum(executor.map(reserve, range(12))), 3)
            with self.assertRaises(UsageLimit):
                UsageStore(path).reserve("new session", 10, daily_requests=3)

    def test_reservation_reconciliation_cooldown_and_day_rollover(self):
        with tempfile.TemporaryDirectory() as directory:
            store = UsageStore(Path(directory) / "usage.db")
            ticket = store.reserve("a", 100, now=86400)
            store.finish(ticket, 50)
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT tokens FROM usage WHERE subject='global'").fetchone()[0], 50)
            with self.assertRaises(UsageLimit):
                store.reserve("a", 10, user_requests=1, now=86401)
            store.reserve("a", 10, user_requests=1, now=172800)
            store.finish(ticket, retry_after=60)
            with self.assertRaises(UsageLimit):
                UsageStore(store.path).reserve("b", 10)

    def test_quota_failure_does_not_call_provider(self):
        store, provider = Mock(), Mock()
        store.reserve.side_effect = UsageLimit("Günlük kullanım sınırı")
        result = call_with_limits(provider, store, "a", "soru", "Genel", [], "", False, api_key="fake", note="")
        self.assertFalse(result.ok)
        provider.assert_not_called()

    def test_supabase_quota_failure_keeps_specific_message_and_skips_provider(self):
        from supabase_store import SupabaseUsageLimit
        store, provider = Mock(), Mock()
        store.reserve.side_effect = SupabaseUsageLimit("Günlük kullanım sınırına ulaşıldı.")
        result = call_with_limits(provider, store, "a", "soru", "Genel", [], "", False, api_key="fake", note="")
        self.assertFalse(result.ok)
        self.assertEqual(result.text, "Günlük kullanım sınırına ulaşıldı.")
        provider.assert_not_called()

    def test_provider_exception_always_closes_reserved_quota(self):
        store, provider = Mock(), Mock(side_effect=RuntimeError("transport details must stay private"))
        store.reserve.return_value = {"request_id": "reservation"}
        result = call_with_limits(provider, store, "a", "soru", "Genel", [], "", False, api_key="fake", note="")
        self.assertFalse(result.ok)
        self.assertIn("beklenmedik", result.text)
        store.finish.assert_called_once_with({"request_id": "reservation"}, 0, 0)

    def test_login_throttle_survives_session_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usage.db"
            for _ in range(20):
                UsageStore(path).login_attempt(now=600)
            with self.assertRaises(UsageLimit):
                UsageStore(path).login_attempt(now=601)
            UsageStore(path).login_attempt(now=901)

    def test_free_minute_budget_is_shared_and_expires(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usage.db"
            UsageStore(path).reserve("a", 4500, now=100)
            with self.assertRaises(UsageLimit):
                UsageStore(path).reserve("b", 3500, now=101)
            UsageStore(path).reserve("b", 3500, now=161)
            with self.assertRaises(UsageLimit):
                UsageStore(path).reserve("c", 8000, now=222)

    def test_utf8_context_is_bounded_without_cutting_characters(self):
        messages = build_messages("Fesih bedeli?", "Genel", [{"role": "user", "content": "eski" * 2000}], "Türkçe belge 🐍 " * 1000)
        self.assertLessEqual(sum(len(m["content"].encode()) + 32 for m in messages), MAX_INPUT_BYTES)
        self.assertNotIn("�", str(messages))

    def test_free_input_limit_prevents_network_call(self):
        provider = Mock()
        result = ask_model("ş" * 6000, "Genel", [], api_key="fake", opener=provider)
        self.assertFalse(result.ok)
        self.assertIn("ücretsiz", result.text)
        provider.assert_not_called()

    def test_multi_sentence_greeting_never_requests_research(self):
        for prompt in ("Merhaba, hazır mısın? Kısa yanıt ver.", "Merhaba hazır mısın?", "Selam! Nasılsın? Kısaca cevap ver."):
            self.assertFalse(wants_research(prompt, True))

    def test_greeting_with_factual_question_still_requests_research(self):
        self.assertTrue(wants_research("Merhaba! Yenimahalle Çözüm Kurs adresini araştır.", True))


if __name__ == "__main__":
    unittest.main()
