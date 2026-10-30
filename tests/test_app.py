"""Headless Streamlit checks; all provider calls are mocked."""
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from model_client import ModelResult
from research import research_record
from email import policy
from email.parser import BytesParser


class AppTests(unittest.TestCase):
    def start(self):
        app = AppTest.from_file("app.py", default_timeout=20).run()
        self.assertFalse(app.exception)
        return app

    def test_initial_screen(self):
        app = self.start()
        self.assertEqual(len(app.chat_input), 1)
        self.assertEqual(len(app.selectbox[0].options), 4)

    def test_success_preserves_repeated_turns(self):
        with patch("model_client.ask_model", return_value=ModelResult("Örnek cevap", ok=True)) as provider:
            app = self.start()
            app.chat_input[0].set_value("Merhaba").run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state["messages"]), 2)
            app.session_state["last_request_at"] = 0
            app.chat_input[0].set_value("Merhaba").run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state["messages"]), 4)
            self.assertEqual(provider.call_count, 2)

    def test_rate_limit_preserves_question_and_blocks_retry(self):
        with patch("model_client.ask_model", return_value=ModelResult("Bekleyin", retry_after=60)) as provider:
            app = self.start()
            app.chat_input[0].set_value("Araştır").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["pending_prompt"], "Araştır")
            self.assertEqual(app.session_state["messages"], [])
            app.run()
            next(b for b in app.button if b.label == "Soruyu yeniden dene").click().run()
            self.assertEqual(provider.call_count, 1)

    def test_clear_content_keeps_cooldown(self):
        app = self.start()
        app.session_state["retry_at"] = 9999999999
        app.session_state["messages"] = [{"role": "user", "content": "özel"}]
        next(b for b in app.button if b.label == "Tüm oturum içeriğini temizle").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["messages"], [])
        self.assertEqual(app.session_state["retry_at"], 9999999999)

    def test_note_is_forwarded_and_cleared_with_chat(self):
        with patch("model_client.ask_model", return_value=ModelResult("Tamam", ok=True)) as provider:
            app = self.start()
            app.text_area[0].set_value("Proje bütçesi 12.000 TL.").run()
            app.chat_input[0].set_value("Planla").run()
            self.assertFalse(app.exception)
            self.assertEqual(provider.call_args.kwargs["note"], "Proje bütçesi 12.000 TL.")
            next(b for b in app.button if b.label == "Sohbeti temizle").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.text_area[0].value, "")
            self.assertEqual(app.session_state["messages"], [])

    def test_source_record_survives_rerun(self):
        ledger = research_record("[Kaynak](https://example.org/data)", True, "2026-10-30T12:00:00+00:00")
        with patch("model_client.ask_model", return_value=ModelResult("Kaynaklı yanıt", ok=True, research=ledger)):
            app = self.start()
            app.checkbox[0].check().run()
            app.chat_input[0].set_value("Güncel veriyi araştır").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["messages"][-1]["research"], ledger)
            self.assertTrue(any("bağımsız doğrulanmadı" in caption.value for caption in app.caption))

    def test_missing_sources_shows_warning(self):
        ledger = research_record("Kaynak bulunamadı", True, "now")
        with patch("model_client.ask_model", return_value=ModelResult("Kaynak bulunamadı", ok=True, research=ledger)):
            app = self.start()
            app.checkbox[0].check().run()
            app.chat_input[0].set_value("Araştır").run()
            self.assertFalse(app.exception)
            self.assertTrue(any("doğrulanmış sayılmamalı" in warning.value for warning in app.warning))

    def test_email_draft_creation_does_not_call_model(self):
        with patch("model_client.ask_model") as provider:
            app = self.start()
            next(w for w in app.text_input if w.label == "Alıcı (tek adres, isteğe bağlı)").set_value("test@example.org").run()
            next(w for w in app.text_input if w.label == "Konu").set_value("Görüşme").run()
            next(w for w in app.text_area if w.label == "İleti metni").set_value("Türkçe ileti").run()
            next(b for b in app.button if b.label == "Taslağı hazırla").click().run()
            self.assertFalse(app.exception)
            message = BytesParser(policy=policy.default).parsebytes(app.session_state["prepared_draft"]["content"])
            self.assertEqual(message["To"], "test@example.org")
            self.assertEqual(message["X-Unsent"], "1")
            self.assertIn("Türkçe ileti", message.get_content())
            provider.assert_not_called()
            next(w for w in app.text_input if w.label == "Konu").set_value("Değişen konu").run()
            self.assertFalse(any("Taslak hazır" in w.value for w in app.success))

    def test_invalid_email_draft_has_no_download(self):
        app = self.start()
        next(b for b in app.button if b.label == "Taslağı hazırla").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Konu" in w.value for w in app.error))
        self.assertNotIn("prepared_draft", app.session_state)

    def test_copy_answer_and_clear_email_fields(self):
        app = self.start()
        app.session_state["messages"] = [{"role": "assistant", "content": "Son yanıt"}]
        app.run()
        next(b for b in app.button if b.label == "Son yanıtı taslağa al").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(next(w for w in app.text_area if w.label == "İleti metni").value, "Son yanıt")
        next(b for b in app.button if b.label == "Tüm oturum içeriğini temizle").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(next(w for w in app.text_area if w.label == "İleti metni").value, "")

    def test_speech_controls_are_opt_in(self):
        with patch("tools_ui.render_speech") as renderer:
            app = self.start()
            app.session_state["messages"] = [{"role": "assistant", "content": "Yanıt"}]
            app.run()
            renderer.assert_not_called()
            next(w for w in app.checkbox if w.label == "Seslendirme denetimlerini aç").check().run()
            self.assertFalse(app.exception)
            self.assertEqual(renderer.call_args.args[1], "Yanıt")

    def test_speech_iframe_is_rendered(self):
        app = self.start()
        app.session_state["messages"] = [{"role": "assistant", "content": "Türkçe ses denemesi"}]
        app.run()
        next(w for w in app.checkbox if w.label == "Seslendirme denetimlerini aç").check().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("iframe")), 1)


if __name__ == "__main__":
    unittest.main()
