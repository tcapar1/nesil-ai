"""Tests for the optional local Ollama provider."""
import json
import os
import unittest
from unittest.mock import patch

from local_model import ask_local_model, local_model_configured, _messages, list_local_models, model_for_mode
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
        self.assertIn("%25 = 25/100 = 0,25 = 1/4", math[0]["content"])
        self.assertIn("Decimal Forma", math[0]["content"])
        self.assertIn("Türkçe virgül", math[0]["content"])
        self.assertIn("Kontrol bölümünde", math[0]["content"])
        self.assertIn("25100 yazma", math[0]["content"])
        self.assertIn("yarım cümle", math[0]["content"])

    def test_general_mode_uses_configured_local_general_model(self):
        with patch.dict(os.environ, {"NESIL_LOCAL_MODEL_ENABLED": "true", "NESIL_OLLAMA_GENERAL_MODEL": "qwen3:4b"}):
            messages = _messages("Metni özetle", "Genel yardımcı", [], "", "")
            self.assertEqual(model_for_mode("Genel yardımcı"), "qwen3:4b")
            self.assertIn("Genel yardımcısın", messages[0]["content"])
            self.assertNotIn("Matematik öğretmenisin", messages[0]["content"])

    def test_model_list_check_is_read_only_and_filters_names(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit=-1):
                return b'{"models":[{"name":"qwen3:4b"},{"name":"bad model"}]}'
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://127.0.0.1:11434"}), \
             patch("local_model.urllib.request.urlopen", return_value=Response()) as opener:
            names, error = list_local_models()
        request = opener.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/tags")
        self.assertEqual(names, ["qwen3:4b"])
        self.assertEqual(error, "")

    def test_explicit_local_model_override_is_used(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit):
                return b'{"message":{"content":"Tamam"}}'
        with patch.dict(os.environ, {"NESIL_LOCAL_MODEL_ENABLED": "true"}), \
             patch("local_model.urllib.request.urlopen", return_value=Response()) as opener:
            result = ask_local_model("Merhaba", "Genel yardımcı", [], model_override="qwen3:1b")
        self.assertTrue(result.ok)
        self.assertEqual(json.loads(opener.call_args.args[0].data)["model"], "qwen3:1b")

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
