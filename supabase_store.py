"""Supabase-backed atomic usage store; service-role credentials stay server-side."""
import json
import os
import urllib.error
import urllib.request


class SupabaseStoreError(RuntimeError):
    pass


class SupabaseUsageStore:
    def __init__(self, url=None, service_key=None, timeout=8):
        self.url = (url or os.environ.get("SUPABASE_URL", "")).rstrip("/")
        self.service_key = service_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        self.timeout = timeout
        if not self.url or not self.service_key:
            raise SupabaseStoreError("Supabase URL ve service-role anahtarı yapılandırılmalı.")
        if not self.url.startswith("https://") and not (
            self.url.startswith("http://localhost") or self.url.startswith("http://127.0.0.1")
        ):
            raise SupabaseStoreError("Supabase adresi HTTPS olmalı.")

    def _rpc(self, name, payload):
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.url}/rest/v1/rpc/{name}", data=body,
            headers={
                "apikey": self.service_key,
                "Authorization": "Bearer " + self.service_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "NesilAI/1.2",
            }, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(65537)
            if len(raw) > 65536:
                raise SupabaseStoreError("Supabase yanıt boyutu sınırı aşıldı.")
            return json.loads(raw.decode("utf-8")) if raw else None
        except urllib.error.HTTPError as exc:
            # Do not include response body, URL query, or credentials in logs/UI.
            try:
                detail = json.loads(exc.read(8192).decode("utf-8", errors="replace"))
                message = detail.get("message", "") if isinstance(detail, dict) else ""
            except Exception:
                message = ""
            mapping = {
                "NESIL_PROVIDER_COOLDOWN": "Sağlayıcı bekleme süresi devam ediyor.",
                "NESIL_MINUTE_LIMIT": "Ortak ücretsiz dakika kotası doldu. Bir dakika sonra yeniden deneyin.",
                "NESIL_DAILY_LIMIT": "Günlük kullanım sınırına ulaşıldı.",
                "NESIL_LOGIN_LIMIT": "Çok fazla giriş denemesi. Beş dakika sonra yeniden deneyin.",
                "NESIL_INVALID_RESERVATION": "Kullanım kotası isteği geçersiz.",
            }
            if message in mapping:
                raise SupabaseStoreError(mapping[message]) from None
            raise SupabaseStoreError("Supabase kullanım kaydı başarısız. Yönetici ayarları ve SQL migration kontrol edilmeli.") from None
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise SupabaseStoreError("Supabase hizmetine erişilemiyor. Model isteği gönderilmedi.") from None

    def reserve(self, subject, estimated_tokens, daily_requests=500, daily_tokens=150000,
                user_requests=100, now=None, minute_requests=20, minute_tokens=7500):
        result = self._rpc("nesil_reserve_usage", {
            "p_subject_hash": str(subject)[:128],
            "p_estimated_tokens": int(estimated_tokens),
            "p_daily_requests": int(daily_requests),
            "p_daily_tokens": int(daily_tokens),
            "p_user_requests": int(user_requests),
            "p_minute_requests": int(minute_requests),
            "p_minute_tokens": int(minute_tokens),
        })
        if isinstance(result, list) and result:
            result = result[0]
        if not isinstance(result, dict) or not result.get("request_id"):
            raise SupabaseStoreError("Supabase kota ayırma yanıtı geçersiz.")
        return result

    def finish(self, reservation, actual_tokens=0, retry_after=0):
        if not isinstance(reservation, dict) or not reservation.get("request_id"):
            raise SupabaseStoreError("Supabase kota işlem kaydı geçersiz.")
        return self._rpc("nesil_finish_usage", {
            "p_request_id": reservation["request_id"],
            "p_actual_tokens": int(actual_tokens or 0),
            "p_retry_after": int(retry_after or 0),
        })

    def login_attempt(self, now=None):
        return self._rpc("nesil_login_attempt", {})


def create_usage_store():
    """Select durable Supabase only when explicitly configured; preserve SQLite dev mode."""
    backend = os.environ.get("NESIL_STORAGE_BACKEND", "sqlite").strip().lower()
    if backend == "supabase":
        return SupabaseUsageStore()
    if backend != "sqlite":
        raise ValueError("NESIL_STORAGE_BACKEND yalnızca sqlite veya supabase olabilir.")
    from usage_limits import UsageStore
    return UsageStore()
