"""Headless Streamlit checks; all provider calls are mocked."""
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from model_client import ModelResult


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


if __name__ == "__main__":
    unittest.main()
