"""Headless Streamlit checks; all provider calls are mocked."""
import unittest
from pathlib import Path
import tempfile
import os
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from model_client import ModelResult
from research import research_record
from email import policy
from email.parser import BytesParser


class AppTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        env = patch.dict(os.environ, {"NESIL_USAGE_DB": str(Path(directory.name) / "usage.db"), "NESIL_USERS_JSON": "{}"})
        env.start()
        self.addCleanup(env.stop)

    def start(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=20).run()
        self.assertFalse(app.exception)
        return app

    def test_initial_screen(self):
        app = self.start()
        self.assertEqual(len(app.chat_input), 1)
        self.assertEqual(len(app.selectbox[0].options), 5)
        self.assertEqual(app.selectbox[1].label, "Model sağlayıcısı")
        self.assertEqual(app.radio[0].label, "Tema")

    def test_dark_theme_preference_is_kept_in_session(self):
        app = self.start()
        app.radio[0].set_value("Koyu").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["theme_choice"], "Koyu")

    def test_continue_answer_queues_followup_with_existing_history(self):
        with patch("app_service.call_with_limits", return_value=ModelResult("Devamı", ok=True)) as provider:
            app = self.start()
            app.session_state["messages"] = [
                {"role": "user", "content": "Rapor özeti"},
                {"role": "assistant", "content": "İlk bölüm"},
            ]
            app.session_state["last_request_at"] = 0
            app.run()
            next(button for button in app.button if button.label == "Yanıtı sürdür").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(provider.call_count, 1)
            self.assertEqual(app.session_state["messages"][-1]["content"], "Devamı")

    def test_regenerate_answer_creates_new_session_turn_without_old_answer_context(self):
        with patch("app_service.call_with_limits", return_value=ModelResult("Yeni yanıt", ok=True)) as provider:
            app = self.start()
            app.session_state["messages"] = [
                {"role": "user", "content": "Önceki konu"},
                {"role": "assistant", "content": "Önceki cevap"},
                {"role": "user", "content": "Aynı soruyu tekrar yanıtla"},
                {"role": "assistant", "content": "Eski cevap"},
            ]
            app.session_state["last_request_at"] = 0
            app.run()
            next(button for button in app.button if button.label == "Yanıtı yeniden üret").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(provider.call_count, 1)
            self.assertEqual(provider.call_args.args[3], "Aynı soruyu tekrar yanıtla")
            self.assertEqual(provider.call_args.args[5], [
                {"role": "user", "content": "Önceki konu"},
                {"role": "assistant", "content": "Önceki cevap"},
            ])
            self.assertEqual(app.session_state["messages"][-1]["content"], "Yeni yanıt")

    def test_login_gate_and_logout(self):
        with patch("model_client.ask_model") as provider:
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=20)
            app.secrets["NESIL_USERS"] = {"ayse": "long-test-access-code"}
            # AppTest secrets are process-global; prevent this login fixture from
            # leaking into later tests that expect the public app configuration.
            self.addCleanup(lambda: app.secrets.pop("NESIL_USERS", None))
            app.run()
            self.assertEqual(len(app.chat_input), 0)
            next(w for w in app.text_input if w.label == "Kullanıcı adı").set_value("ayse")
            next(w for w in app.text_input if w.label == "Erişim kodu").set_value("wrong")
            next(b for b in app.button if b.label == "Giriş yap").click().run()
            self.assertEqual(len(app.chat_input), 0)
            next(w for w in app.text_input if w.label == "Erişim kodu").set_value("long-test-access-code")
            next(b for b in app.button if b.label == "Giriş yap").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.chat_input), 1)
            next(b for b in app.button if b.label == "Çıkış yap").click().run()
            self.assertEqual(len(app.chat_input), 0)
            provider.assert_not_called()

    def test_source_review_uses_evidence_once(self):
        ledger = research_record("https://data.tuik.gov.tr/page", True, "now")
        ledger["question"] = "Önceki soru"
        ledger["sources"][0].update(content_status="retrieved", accessed_at="now", excerpt="Kanıt: 123")
        with patch("model_client.ask_model", return_value=ModelResult("Karşılaştırma", ok=True)) as provider:
            app = self.start()
            app.session_state["messages"] = [{"role": "assistant", "content": "Eski yanıt", "research": ledger}]
            app.run()
            next(b for b in app.button if b.label == "Yanıtı kaynak metniyle karşılaştır").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(provider.call_count, 1)
            self.assertIn("Kanıt: 123", provider.call_args.args[3])
            self.assertFalse(provider.call_args.args[4])
            app.run()
            self.assertEqual(provider.call_count, 1)

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
            next(w for w in app.checkbox if w.label == "İnternette araştır").check().run()
            app.chat_input[0].set_value("Güncel veriyi araştır").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["messages"][-1]["research"], ledger)
            self.assertTrue(any("bağımsız doğrulanmadı" in caption.value for caption in app.caption))

    def test_missing_sources_shows_warning(self):
        ledger = research_record("Kaynak bulunamadı", True, "now")
        with patch("model_client.ask_model", return_value=ModelResult("Kaynak bulunamadı", ok=True, research=ledger)):
            app = self.start()
            next(w for w in app.checkbox if w.label == "İnternette araştır").check().run()
            app.chat_input[0].set_value("Araştır").run()
            self.assertFalse(app.exception)
            self.assertTrue(any("doğrulanmış sayılmamalı" in warning.value for warning in app.warning))

    def test_email_draft_creation_does_not_call_model(self):
        with patch("model_client.ask_model") as provider:
            app = self.start()
            next(w for w in app.text_input if w.label == "Alıcı (tek adres, isteğe bağlı)").set_value("test@example.org")
            next(w for w in app.text_input if w.label == "Konu").set_value("Görüşme")
            next(w for w in app.text_area if w.label == "İleti metni").set_value("Türkçe ileti")
            next(b for b in app.button if b.label == "Taslağı hazırla").click().run()
            self.assertFalse(app.exception)
            message = BytesParser(policy=policy.default).parsebytes(app.session_state["prepared_draft"]["content"])
            self.assertEqual(message["To"], "test@example.org")
            self.assertEqual(message["X-Unsent"], "1")
            self.assertIn("Türkçe ileti", message.get_content())
            provider.assert_not_called()
            self.assertFalse(any(w.label == "Konu" for w in app.text_input))
            next(b for b in app.button if b.label == "Taslağı düzenle").click().run()
            self.assertEqual(next(w for w in app.text_input if w.label == "Konu").value, "Görüşme")
            self.assertEqual(next(w for w in app.text_input if w.label == "Alıcı (tek adres, isteğe bağlı)").value, "test@example.org")
            self.assertEqual(next(w for w in app.text_area if w.label == "İleti metni").value, "Türkçe ileti")
            self.assertNotIn("prepared_draft", app.session_state)
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
        self.assertNotIn("draft_fields", app.session_state)

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

    def test_page_checks_are_opt_in_bounded_and_throttled(self):
        ledger = research_record(" ".join(f"https://data.tuik.gov.tr/page{i}" for i in range(4)), True, "now")
        details = {"content_status": "retrieved", "verified": False, "accessed_at": "2026-10-30T12:00:00Z", "source_title": "Test bülteni", "published_at": "2026-02-09", "data_period": "2025", "excerpt": "Sentetik sayfa metni", "date_conflict": False}
        with patch("research_ui.check_source", return_value=details) as checker, patch("model_client.ask_model") as provider:
            app = self.start()
            app.session_state["messages"] = [{"role": "assistant", "content": "Test", "research": ledger}]
            app.run()
            checker.assert_not_called()
            next(b for b in app.button if b.label == "Kaynak sayfalarını kontrol et").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(checker.call_count, 3)
            sources = app.session_state["messages"][0]["research"]["sources"]
            self.assertEqual(sources[0]["content_status"], "retrieved")
            self.assertFalse(sources[0]["verified"])
            self.assertNotIn("content_status", sources[3])
            self.assertTrue(any("iddiaların doğruluğu" in w.value for w in app.caption))
            next(b for b in app.button if b.label == "Kaynak sayfalarını kontrol et").click().run()
            self.assertEqual(checker.call_count, 3)
            cooldown = app.session_state["source_retry_at"]
            next(b for b in app.button if b.label == "Tüm oturum içeriğini temizle").click().run()
            self.assertEqual(app.session_state["source_retry_at"], cooldown)
            provider.assert_not_called()

    def test_page_check_error_does_not_break_chat(self):
        ledger = research_record("https://data.tuik.gov.tr/page", True, "now")
        with patch("research_ui.check_source", side_effect=RuntimeError("secret details")):
            app = self.start()
            app.session_state["messages"] = [{"role": "assistant", "content": "Test", "research": ledger}]
            app.run()
            next(b for b in app.button if b.label == "Kaynak sayfalarını kontrol et").click().run()
            self.assertFalse(app.exception)
            source = app.session_state["messages"][0]["research"]["sources"][0]
            self.assertEqual(source["content_status"], "unavailable")
            self.assertNotIn("secret", str(source))

    def test_multiple_source_records_have_distinct_buttons(self):
        from copy import deepcopy
        ledger = research_record("https://data.tuik.gov.tr/page", True, "now")
        app = self.start()
        app.session_state["messages"] = [{"role": "assistant", "content": "Test", "research": deepcopy(ledger)} for _ in range(2)]
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len([b for b in app.button if b.label == "Kaynak sayfalarını kontrol et"]), 2)

    def test_coding_mode_routes_to_local_provider(self):
        with patch.dict(os.environ, {"NESIL_LOCAL_MODEL_ENABLED": "true"}), \
             patch("local_model.ask_local_model", return_value=ModelResult("Yerel cevap", ok=True)) as local_provider, \
             patch("app_service.call_with_limits") as cloud_provider:
            app = self.start()
            app.selectbox[0].select("Kodlama yardımcısı").run()
            self.assertEqual(app.selectbox[0].value, "Kodlama yardımcısı")
            app.session_state["pending_prompt"] = "Python fonksiyonu yaz"
            app.session_state["last_request_at"] = 0
            app.run()
            next(b for b in app.button if b.label == "Soruyu yeniden dene").click().run()
            self.assertFalse(app.exception)
            local_provider.assert_called_once()
            cloud_provider.assert_not_called()
            self.assertEqual(app.session_state["messages"][-1]["content"], "Yerel cevap")

    def test_math_mode_routes_to_local_provider(self):
        with patch.dict(os.environ, {"NESIL_LOCAL_MODEL_ENABLED": "true"}), \
             patch("local_model.ask_local_model", return_value=ModelResult("Matematik cevabı", ok=True)) as local_provider, \
             patch("app_service.call_with_limits") as cloud_provider:
            app = self.start()
            app.selectbox[0].select("Matematik öğretmeni").run()
            self.assertEqual(app.selectbox[0].value, "Matematik öğretmeni")
            app.session_state["pending_prompt"] = "2+2 kaçtır?"
            app.session_state["last_request_at"] = 0
            app.run()
            next(b for b in app.button if b.label == "Soruyu yeniden dene").click().run()
            self.assertFalse(app.exception)
            local_provider.assert_called_once()
            cloud_provider.assert_not_called()


if __name__ == "__main__":
    unittest.main()
