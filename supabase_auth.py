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
            # Surface only Supabase's machine-readable error code, never raw response details.
            status = exc.code
            try:
                body = json.loads(exc.read(8192).decode("utf-8"))
            except Exception:
                body = {}
            code = str(body.get("code") or body.get("error_code") or "").lower()
            provider_message = str(body.get("message") or body.get("msg") or body.get("error_description") or "").lower()
            if status == 401 and any(term in provider_message for term in ("api key", "apikey", "invalid api", "missing api")):
                raise SupabaseAuthError("Supabase API anahtarı geçersiz veya URL ile aynı projeye ait değil. Streamlit Secrets içindeki SUPABASE_URL ve SUPABASE_PUBLISHABLE_KEY değerlerini aynı Supabase projesinden yeniden alın.") from None
            safe_messages = {
                "invalid_credentials": "E-posta veya şifre yanlış. Supabase'de bu kullanıcı için şifreyi sıfırlayın.",
                "email_not_confirmed": "E-posta doğrulanmamış. Supabase Users ekranındaki Confirmed alanını kontrol edin.",
                "user_not_found": "Bu e-posta ile kullanıcı bulunamadı.",
                "user_banned": "Bu kullanıcı hesabı engellenmiş.",
                "signup_disabled": "Supabase Email kayıtları kapalı.",
                "over_email_send_rate_limit": "E-posta gönderim sınırına ulaşıldı. Bir süre bekleyin.",
                "over_request_rate_limit": "Çok fazla istek gönderildi. Bir süre bekleyin.",
                "weak_password": "Şifre güvenlik koşullarını karşılamıyor.",
            }
            if code in safe_messages:
                raise SupabaseAuthError(f"Supabase ({code}): {safe_messages[code]}") from None
            if status == 429:
                raise SupabaseAuthError("Supabase (rate_limit): Çok fazla deneme. Bir süre sonra yeniden deneyin.") from None
            if status in (400, 401, 422):
                raise SupabaseAuthError(f"Supabase (HTTP {status}, {code or 'auth_error'}): Giriş reddedildi. Supabase Auth Logs bölümünü kontrol edin.") from None
            raise SupabaseAuthError(f"Supabase (HTTP {status}): Kimlik hizmeti isteği tamamlayamadı.") from None
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
        setting("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY"),
    )
