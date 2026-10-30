"""Supabase Auth REST client. Tokens stay in the Streamlit server session."""
import json
import urllib.error
import urllib.request


class SupabaseAuthError(ValueError):
    pass


class SupabaseAuthClient:
    def __init__(self, url, anon_key, timeout=8):
        self.url = (url or "").rstrip("/")
        self.anon_key = anon_key or ""
        self.timeout = timeout
        if not self.url or not self.anon_key:
            raise SupabaseAuthError("Supabase URL ve public/publishable API anahtarı yapılandırılmalı.")
        if not self.url.startswith("https://") and not self.url.startswith(("http://localhost", "http://127.0.0.1")):
            raise SupabaseAuthError("Supabase adresi HTTPS olmalı.")

    def _request(self, path, payload=None, access_token=None):
        headers = {"apikey": self.anon_key, "Content-Type": "application/json",
                   "Accept": "application/json", "User-Agent": "NesilAI/1.3"}
        if access_token:
            headers["Authorization"] = "Bearer " + access_token
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.url + path, data=data, headers=headers,
                                         method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(65537)
            if len(raw) > 65536:
                raise SupabaseAuthError("Supabase kimlik doğrulama yanıtı çok büyük.")
            result = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(result, dict):
                raise SupabaseAuthError("Supabase kimlik doğrulama yanıtı geçersiz.")
            return result
        except urllib.error.HTTPError as exc:
            # Do not expose provider response bodies: they can contain user details.
            status = exc.code
            if status in (400, 401, 422):
                raise SupabaseAuthError("E-posta/şifre bilgileri geçersiz veya e-posta doğrulaması gerekiyor.") from None
            if status == 429:
                raise SupabaseAuthError("Çok fazla giriş denemesi. Bir süre sonra yeniden deneyin.") from None
            raise SupabaseAuthError("Supabase kimlik hizmeti isteği tamamlayamadı.") from None
        except (urllib.error.URLError, TimeoutError):
            raise SupabaseAuthError("Supabase kimlik hizmetine erişilemiyor.") from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SupabaseAuthError("Supabase kimlik hizmetinden geçersiz yanıt alındı.") from None

    def sign_up(self, email, password):
        return self._request("/auth/v1/signup", {"email": email.strip(), "password": password})

    def sign_in(self, email, password):
        result = self._request("/auth/v1/token?grant_type=password",
                               {"email": email.strip(), "password": password})
        if not result.get("access_token") or not result.get("refresh_token") or not result.get("user", {}).get("id"):
            raise SupabaseAuthError("Giriş tamamlanmadı. E-posta doğrulaması gerekiyorsa gelen kutunuzu kontrol edin.")
        return result

    def refresh(self, refresh_token):
        result = self._request("/auth/v1/token?grant_type=refresh_token",
                               {"refresh_token": refresh_token})
        if not result.get("access_token") or not result.get("refresh_token"):
            raise SupabaseAuthError("Oturum yenilenemedi. Yeniden giriş yapın.")
        return result

    def sign_out(self, access_token):
        self._request("/auth/v1/logout", {}, access_token=access_token)


def create_auth_client(secrets=None):
    """Read Streamlit Secrets first; environment variables are the local fallback."""
    if secrets is None:
        try:
            import streamlit as st
            secrets = st.secrets
        except Exception:
            secrets = {}

    def setting(*keys):
        for key in keys:
            try:
                value = secrets.get(key)
            except Exception:
                value = None
            if value not in (None, ""):
                return str(value)
            import os
            value = os.environ.get(key)
            if value:
                return value
        return ""

    return SupabaseAuthClient(
        setting("SUPABASE_URL"),
        setting("SUPABASE_ANON_KEY", "SUPABASE_PUBLISHABLE_KEY"),
    )
