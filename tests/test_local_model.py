"""Tests for the optional local Ollama provider."""
import json
import os
import unittest
from unittest.mock import patch

from local_model import ask_local_model, local_model_configured, _messages
from model_client import ModelResult


class LocalModelTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(local_model_configured())
            result = ask_local_model("Merhaba", "Kodlama yardımcısı", [])
            self.assertFalse(result.ok)
            self.assertIn("Ollama", result.text)

    def test_mode_specific_system_prompts(self):
        coding = _messages("Bir Python fonksiyonu yaz", "Kodlama yardımcısı", [], "", "")
        math = _messages("2+2 kaçtır?", "Matematik öğretmeni", [], "", "")
        self.assertIn("Kodlama uzmanısın", coding[0]["content"])
        self.assertIn("Matematik öğretmenisin", math[0]["content"])

    def test_unsupported_mode_rejected(self):
        with patch.dict(os.environ, {"NESIL_LOCAL_MODEL_ENABLED": "true"}):
            result = ask_local_model("test", "Genel yardımcı", [])
        self.assertFalse(result.ok)
        self.assertIn("yalnızca kodlama", result.text)

    def test_local_request_uses_expected_model_and_never_groq(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, limit):
                return json.dumps({"message": {"content": "Çözüm hazır."}, "prompt_eval_count": 10, "eval_count": 5}).encode()
        with patch.dict(os.environ, {"NESIL_LOCAL_MODEL_ENABLED": "true", "OLLAMA_BASE_URL": "http://127.0.0.1:11434"}), \
             patch("local_model.urllib.request.urlopen", return_value=Response()) as opener:
            result = ask_local_model("Bir fonksiyon yaz", "Kodlama yardımcısı", [])
        self.assertTrue(result.ok)
        self.assertEqual(result.text, "Çözüm hazır.")
        request = opener.call_args.args[0]
        payload = json.loads(request.data.decode())
        self.assertEqual(payload["model"], "qwen2.5-coder:3b")
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(result.usage["total_tokens"], 15)

    def test_missing_model_is_explained(self):
        from urllib.error import HTTPError
        error = HTTPError("http://127.0.0.1:11434/api/chat", 404, "not found", {}, None)
        with patch.dict(os.environ, {"NESIL_LOCAL_MODEL_ENABLED": "true"}), \
             patch("local_model.urllib.request.urlopen", side_effect=error):
            result = ask_local_model("2+2", "Matematik öğretmeni", [])
        self.assertFalse(result.ok)
        self.assertIn("qwen3:4b", result.text)


if __name__ == "__main__":
    unittest.main()
