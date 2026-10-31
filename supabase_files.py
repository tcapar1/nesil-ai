"""Private per-user document storage using Supabase Storage and the user's JWT."""
import json
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
import uuid


BUCKET = "nesil-user-files"
MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {"txt", "md", "json", "py", "log", "csv", "pdf", "docx", "xlsx", "xlsm"}


class SupabaseFileError(ValueError):
    pass


class SupabaseFileStore:
    def __init__(self, url, public_key, access_token, user_id, timeout=15):
        self.url = (url or "").rstrip("/")
        self.public_key = public_key or ""
        self.access_token = access_token or ""
        self.user_id = str(user_id or "")
        self.timeout = timeout
        if not all((self.url, self.public_key, self.access_token, self.user_id)):
            raise SupabaseFileError("Supabase dosya alanı yapılandırılmamış.")
        if not self.url.startswith("https://") and not self.url.startswith(("http://localhost", "http://127.0.0.1")):
            raise SupabaseFileError("Supabase adresi HTTPS olmalı.")

    def _request(self, method, path, body=None, content_type=None):
        headers = {"apikey": self.public_key, "Authorization": "Bearer " + self.access_token,
                   "Accept": "application/json", "User-Agent": "NesilAI/1.3"}
        if content_type:
            headers["Content-Type"] = content_type
        if body is not None and content_type == "application/json":
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.url + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(MAX_FILE_BYTES + 65537)
            if len(raw) > MAX_FILE_BYTES + 65536:
                raise SupabaseFileError("Dosya hizmetinden gelen yanıt izin verilen boyutu aşıyor.")
            return raw
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise SupabaseFileError("Oturumun süresi dolmuş. Yeniden giriş yapın.") from None
            if exc.code == 403:
                raise SupabaseFileError("Bu dosyaya erişim izniniz yok.") from None
            if exc.code == 404:
                raise SupabaseFileError("Özel dosya alanı bulunamadı. Supabase Storage migration dosyasını uygulayın.") from None
            if exc.code == 409:
                raise SupabaseFileError("Aynı dosya kaydı zaten mevcut.") from None
            raise SupabaseFileError("Dosya işlemi tamamlanamadı.") from None
        except (urllib.error.URLError, TimeoutError):
            raise SupabaseFileError("Supabase dosya alanına erişilemiyor.") from None

    def _object_path(self, filename):
        safe = urllib.parse.quote(filename, safe="._-")
        return f"{self.user_id}/{safe}"

    def upload(self, filename, raw):
        name = str(filename or "").replace("\\", "/").split("/")[-1].strip()
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if not name or len(name) > 180 or ext not in ALLOWED_EXTENSIONS:
            raise SupabaseFileError("Dosya adı veya türü desteklenmiyor.")
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_FILE_BYTES:
            raise SupabaseFileError("Dosya boş veya 10 MB sınırını aşıyor.")
        # Random prefix prevents collisions and avoids overwriting an earlier upload.
        object_name = f"{self.user_id}/{uuid.uuid4().hex}_{name}"
        path = "/storage/v1/object/" + BUCKET + "/" + "/".join(urllib.parse.quote(p, safe="._-") for p in object_name.split("/"))
        mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
        self._request("POST", path, raw, mime)
        return {"name": name, "path": object_name, "size": len(raw), "content_type": mime}

    def list_files(self, limit=100):
        payload = {"prefix": self.user_id + "/", "limit": max(1, min(int(limit), 100)), "offset": 0,
                   "sortBy": {"column": "created_at", "order": "desc"}}
        raw = self._request("POST", "/storage/v1/object/list/" + BUCKET, payload, "application/json")
        try:
            rows = json.loads(raw.decode("utf-8")) if raw else []
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SupabaseFileError("Dosya listesi geçersiz yanıt verdi.") from None
        if not isinstance(rows, list):
            raise SupabaseFileError("Dosya listesi beklenen biçimde değil.")
        return [{"name": str(row.get("name", "")), "id": row.get("id"),
                 "metadata": row.get("metadata") or {}, "created_at": row.get("created_at")}
                for row in rows if isinstance(row, dict) and row.get("name")]

    def download(self, object_path):
        self._validate_path(object_path)
        path = "/storage/v1/object/authenticated/" + BUCKET + "/" + "/".join(
            urllib.parse.quote(part, safe="._-") for part in object_path.split("/")
        )
        # Download cap is one original upload plus small HTTP overhead.
        return self._request("GET", path)

    def delete(self, object_path):
        self._validate_path(object_path)
        self._request("POST", "/storage/v1/object/" + BUCKET, {"prefixes": [object_path]}, "application/json")

    def _validate_path(self, object_path):
        if not isinstance(object_path, str) or not object_path.startswith(self.user_id + "/") or ".." in object_path.split("/"):
            raise SupabaseFileError("Dosya yolu bu kullanıcıya ait değil.")


def create_file_store(secrets, access_token, user_id):
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
    return SupabaseFileStore(setting("SUPABASE_URL"),
                             setting("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY"),
                             access_token, user_id)
