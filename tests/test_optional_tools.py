import base64
from email import policy
from email.parser import BytesParser
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace

from email_draft import build_draft
from voice import MAX_SPEECH, speech_html, render_speech
from report_export import MAX_REPORT_CHARS, make_docx, make_pdf


class EmailTests(unittest.TestCase):
    def test_turkish_plain_text_unsent_roundtrip(self):
        raw = build_draft("test@example.org", "Görüşme özeti", "Merhaba,\nİş planı ektedir.\n<script>bu HTML değildir</script>")
        message = BytesParser(policy=policy.default).parsebytes(raw)
        self.assertEqual(message["To"], "test@example.org")
        self.assertEqual(message["Subject"], "Görüşme özeti")
        self.assertEqual(message["X-Unsent"], "1")
        self.assertEqual(message.get_content_type(), "text/plain")
        self.assertIn("İş planı", message.get_content())
        self.assertNotIn("From", message)
        self.assertNotIn("Bcc", message)

    def test_header_injection_rejected(self):
        for recipient, subject in (("a@example.org\r\nBcc: b@example.org", "Konu"), ("a@example.org", "Konu\nBcc: b@example.org"), ("", "Konu\x01")):
            with self.assertRaises(ValueError):
                build_draft(recipient, subject, "İleti")

    def test_address_limits_and_no_multiple_recipients(self):
        for recipient in ("bad", "a@example.org,b@example.org", "Ad <a@example.org>", "a@-example.org", ".a@example.org", "a..b@example.org", "a" * 65 + "@example.org"):
            with self.subTest(recipient=recipient), self.assertRaises(ValueError):
                build_draft(recipient, "Konu", "İleti")

    def test_empty_recipient_is_an_unaddressed_draft(self):
        message = BytesParser(policy=policy.default).parsebytes(build_draft("", "Konu", "İleti"))
        self.assertNotIn("To", message)

    def test_empty_and_oversized_content(self):
        for subject, body in (("", "İleti"), ("x" * 201, "İleti"), ("Konu", " "), ("Konu", "x" * 30001), ("Konu", "a\x00b")):
            with self.assertRaises(ValueError):
                build_draft("", subject, body)


class VoiceTests(unittest.TestCase):
    def test_untrusted_answer_only_appears_as_base64_data(self):
        malicious = '</script><img src=x onerror="alert(1)"> Türkçe 😀'
        html = speech_html(malicious)
        self.assertNotIn(malicious, html)
        self.assertEqual(html.count("<script>"), 1)
        encoded = re.search(r'atob\("([A-Za-z0-9+/=]*)"\)', html).group(1)
        self.assertEqual(base64.b64decode(encoded).decode(), malicious)
        self.assertIn("connect-src 'none'", html)

    def test_speech_length_is_bounded(self):
        html = speech_html("ö" * (MAX_SPEECH + 1))
        encoded = re.search(r'atob\("([A-Za-z0-9+/=]*)"\)', html).group(1)
        self.assertEqual(len(base64.b64decode(encoded).decode()), MAX_SPEECH)

    def test_new_streamlit_iframe_adapter(self):
        calls = []
        fake = SimpleNamespace(iframe=lambda *a, **kw: calls.append((a, kw)), caption=lambda text: None)
        render_speech(fake, "Test")
        self.assertEqual(len(calls), 1)
        self.assertIn("speechSynthesis", calls[0][0][0])

    @unittest.skipUnless(shutil.which("node"), "Node.js required for simulated speech controls")
    def test_javascript_speech_controls(self):
        script = re.search(r"<script>(.*?)</script>", speech_html("Türkçe </script> veri"), re.S).group(1)
        runner = Path(__file__).with_name("test_speech.cjs")
        result = subprocess.run([shutil.which("node"), str(runner)], input=script,
                                text=True, encoding="utf-8", capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class ReportExportTests(unittest.TestCase):
    def test_word_report_contains_turkish_answer(self):
        from docx import Document

        content = make_docx("İş planı\nİkinci bölüm")
        self.assertTrue(content.startswith(b"PK"))
        path = Path(__file__).with_name("_temporary_report_test.docx")
        try:
            path.write_bytes(content)
            document = Document(path)
            self.assertIn("İş planı", "\n".join(p.text for p in document.paragraphs))
        finally:
            path.unlink(missing_ok=True)

    def test_pdf_export_requires_unicode_font_and_produces_pdf(self):
        from pypdf import PdfReader

        content = make_pdf("Türkçe karakterler: ığüşöç İŞ")
        self.assertTrue(content.startswith(b"%PDF"))
        import io
        extracted = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
        self.assertIn("Türkçe karakterler", extracted)

    def test_empty_and_oversized_reports_are_rejected(self):
        for text in ("", "  ", "x" * (MAX_REPORT_CHARS + 1)):
            with self.subTest(length=len(text)), self.assertRaises(ValueError):
                make_docx(text)


if __name__ == "__main__":
    unittest.main()
