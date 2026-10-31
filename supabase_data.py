"""User-scoped Supabase PostgREST storage; all calls use the user's JWT and RLS."""
import json
import urllib.error
import urllib.parse
import urllib.request


class SupabaseDataError(ValueError):
    pass


class SupabaseDataStore:
    def __init__(self, url, anon_key, access_token, user_id, timeout=8):
        self.url = (url or "").rstrip("/")
        self.anon_key = anon_key or ""
        self.access_token = access_token or ""
        self.user_id = user_id or ""
        self.timeout = timeout
        if not self.url or not self.anon_key or not self.access_token or not self.user_id:
            raise SupabaseDataError("Supabase kullanıcı oturumu yapılandırılmamış.")
        if not self.url.startswith("https://") and not self.url.startswith(("http://localhost", "http://127.0.0.1")):
            raise SupabaseDataError("Supabase adresi HTTPS olmalı.")

    def _request(self, method, table, query="", payload=None, prefer=None):
        url = self.url + "/rest/v1/" + table + (("?" + query) if query else "")
        headers = {"apikey": self.anon_key, "Authorization": "Bearer " + self.access_token,
                   "Accept": "application/json", "Content-Type": "application/json",
                   "User-Agent": "NesilAI/1.3"}
        if prefer:
            headers["Prefer"] = prefer
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise SupabaseDataError("Veritabanı yanıtı izin verilen boyutu aşıyor.")
            if not raw:
                return []
            result = json.loads(raw.decode("utf-8"))
            if not isinstance(result, list):
                raise SupabaseDataError("Veritabanı yanıtı beklenen biçimde değil.")
            return result
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise SupabaseDataError("Oturumun süresi dolmuş. Yeniden giriş yapın.") from None
            if exc.code == 403:
                raise SupabaseDataError("Bu kayıt için erişim izniniz yok.") from None
            if exc.code == 404:
                raise SupabaseDataError("Veritabanı tablosu bulunamadı. SQL migration dosyalarını uygulayın.") from None
            raise SupabaseDataError("Veritabanı işlemi tamamlanamadı.") from None
        except (urllib.error.URLError, TimeoutError):
            raise SupabaseDataError("Supabase veritabanına erişilemiyor.") from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SupabaseDataError("Veritabanından geçersiz yanıt alındı.") from None

    def get_profile(self):
        q = urllib.parse.urlencode({"select": "user_id,display_name,created_at,updated_at",
                                    "user_id": "eq." + self.user_id, "limit": "1"})
        rows = self._request("GET", "nesil_profiles", q)
        return rows[0] if rows else {"user_id": self.user_id, "display_name": ""}

    def update_profile(self, display_name):
        if not isinstance(display_name, str) or len(display_name.strip()) > 80:
            raise SupabaseDataError("Görünen ad en fazla 80 karakter olabilir.")
        # Upsert also repairs accounts created before the profile trigger existed.
        q = urllib.parse.urlencode({
            "on_conflict": "user_id",
            "select": "user_id,display_name,updated_at",
        })
        rows = self._request(
            "POST", "nesil_profiles", q,
            {"user_id": self.user_id, "display_name": display_name.strip()},
            "resolution=merge-duplicates,return=representation",
        )
        if not rows:
            raise SupabaseDataError("Profil kaydı oluşturulamadı veya güncellenemedi.")
        return rows[0]

    def list_conversations(self, limit=50, include_archived=False):
        limit = max(1, min(int(limit), 100))
        filters = {
            "select": "id,title,is_pinned,is_archived,created_at,updated_at",
            "order": "is_pinned.desc,updated_at.desc",
            "limit": str(limit),
        }
        if not include_archived:
            filters["is_archived"] = "eq.false"
        q = urllib.parse.urlencode(filters)
        return self._request("GET", "nesil_conversations", q)

    def create_conversation(self, title="Yeni sohbet"):
        title = (title or "Yeni sohbet").strip()[:120] or "Yeni sohbet"
        q = urllib.parse.urlencode({"select": "id,title,created_at,updated_at"})
        rows = self._request("POST", "nesil_conversations", q, {"user_id": self.user_id, "title": title}, "return=representation")
        if not rows or not rows[0].get("id"):
            raise SupabaseDataError("Yeni sohbet kaydı oluşturulamadı.")
        return rows[0]

    def set_conversation_flag(self, conversation_id, flag, value):
        if not isinstance(conversation_id, str) or not conversation_id or len(conversation_id) > 64:
            raise SupabaseDataError("Sohbet kimliği geçersiz.")
        if flag not in ("is_pinned", "is_archived") or not isinstance(value, bool):
            raise SupabaseDataError("Sohbet ayarı geçersiz.")
        q = urllib.parse.urlencode({"id": "eq." + conversation_id})
        self._request("PATCH", "nesil_conversations", q,
                      {flag: value,
                       "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()},
                      "return=minimal")

    def pin_conversation(self, conversation_id, pinned=True):
        self.set_conversation_flag(conversation_id, "is_pinned", pinned)

    def archive_conversation(self, conversation_id, archived=True):
        self.set_conversation_flag(conversation_id, "is_archived", archived)

    def list_messages(self, conversation_id, limit=100):
        q = urllib.parse.urlencode({"select": "id,role,content,created_at",
                                    "conversation_id": "eq." + str(conversation_id),
                                    "order": "created_at.asc,id.asc", "limit": str(max(1, min(int(limit), 200)))})
        return self._request("GET", "nesil_messages", q)

    def add_message(self, conversation_id, role, content):
        if role not in ("user", "assistant") or not isinstance(content, str) or len(content) > 50000:
            raise SupabaseDataError("Mesaj biçimi veya uzunluğu geçersiz.")
        q = urllib.parse.urlencode({"select": "id,role,content,created_at"})
        rows = self._request("POST", "nesil_messages", q,
                             {"conversation_id": str(conversation_id), "role": role, "content": content},
                             "return=representation")
        if not rows:
            raise SupabaseDataError("Mesaj kaydedilemedi.")
        return rows[0]

    def add_messages(self, conversation_id, messages):
        """Insert a message batch in one PostgREST/PostgreSQL statement."""
        if not isinstance(conversation_id, str) or not conversation_id or len(conversation_id) > 64:
            raise SupabaseDataError("Sohbet kimliği geçersiz.")
        if not isinstance(messages, (list, tuple)) or not 1 <= len(messages) <= 100:
            raise SupabaseDataError("Mesaj grubu boş veya çok büyük.")
        payload = []
        for message in messages:
            if not isinstance(message, dict):
                raise SupabaseDataError("Mesaj biçimi geçersiz.")
            role, content = message.get("role"), message.get("content")
            if role not in ("user", "assistant") or not isinstance(content, str) or len(content) > 50000:
                raise SupabaseDataError("Mesaj biçimi veya uzunluğu geçersiz.")
            payload.append({"conversation_id": conversation_id, "role": role, "content": content})
        if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > 1_000_000:
            raise SupabaseDataError("Mesaj grubu 1 MB sınırını aşıyor.")
        self._request("POST", "nesil_messages", payload=payload, prefer="return=minimal")

    def delete_conversation(self, conversation_id):
        """Delete one owned conversation; RLS verifies ownership and cascades its messages."""
        if not isinstance(conversation_id, str) or not conversation_id or len(conversation_id) > 64:
            raise SupabaseDataError("Sohbet kimliği geçersiz.")
        q = urllib.parse.urlencode({"id": "eq." + conversation_id})
        self._request("DELETE", "nesil_conversations", q, prefer="return=minimal")

    def touch_conversation(self, conversation_id):
        """Move a conversation to the top of the user's recent history."""
        if not isinstance(conversation_id, str) or not conversation_id or len(conversation_id) > 64:
            raise SupabaseDataError("Sohbet kimliği geçersiz.")
        q = urllib.parse.urlencode({"id": "eq." + conversation_id})
        updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        self._request("PATCH", "nesil_conversations", q, {"updated_at": updated_at}, "return=minimal")

    def update_conversation_title(self, conversation_id, title):
        if not isinstance(conversation_id, str) or not conversation_id or len(conversation_id) > 64:
            raise SupabaseDataError("Sohbet kimliği geçersiz.")
        if not isinstance(title, str) or len(title.strip()) > 120:
            raise SupabaseDataError("Sohbet başlığı en fazla 120 karakter olabilir.")
        q = urllib.parse.urlencode({"id": "eq." + conversation_id})
        self._request("PATCH", "nesil_conversations", q,
                      {"title": title.strip() or "Yeni sohbet",
                       "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}, "return=minimal")

    def list_documents(self, search="", folder="", limit=100):
        filters = {
            "select": "id,object_path,file_name,folder_name,tags,file_size,content_type,created_at,updated_at",
            "order": "updated_at.desc",
            "limit": str(max(1, min(int(limit), 100))),
        }
        if folder:
            if not isinstance(folder, str) or len(folder) > 80:
                raise SupabaseDataError("Klasör adı geçersiz.")
            filters["folder_name"] = "eq." + folder
        if search:
            if not isinstance(search, str) or len(search.strip()) > 100:
                raise SupabaseDataError("Arama metni en fazla 100 karakter olabilir.")
            term = search.strip().replace("*", "").replace("%", "").replace(",", " ")
            if term:
                filters["file_name"] = "ilike.*" + term + "*"
        return self._request("GET", "nesil_documents", urllib.parse.urlencode(filters))

    def add_document(self, object_path, file_name, file_size, content_type):
        if not isinstance(object_path, str) or not object_path.startswith(self.user_id + "/") or ".." in object_path.split("/"):
            raise SupabaseDataError("Belge yolu bu hesaba ait değil.")
        if not isinstance(file_name, str) or not file_name.strip() or len(file_name) > 180:
            raise SupabaseDataError("Dosya adı geçersiz.")
        if not isinstance(file_size, int) or file_size < 1 or file_size > 10 * 1024 * 1024:
            raise SupabaseDataError("Dosya boyutu geçersiz.")
        select = "id,object_path,file_name,folder_name,tags,file_size,content_type,created_at,updated_at"
        q = urllib.parse.urlencode({"select": select, "on_conflict": "object_path"})
        rows = self._request("POST", "nesil_documents", q, {
            "user_id": self.user_id, "object_path": object_path, "file_name": file_name.strip(),
            "file_size": file_size, "content_type": (content_type or "application/octet-stream")[:120],
            "folder_name": "Genel", "tags": [],
        }, "resolution=ignore-duplicates,return=representation")
        if rows:
            return rows[0]
        # The same idempotent upload may have completed its metadata write before
        # the client timed out. Return the already-owned row without overwriting tags.
        lookup = urllib.parse.urlencode({"select": select, "object_path": "eq." + object_path, "limit": "1"})
        existing = self._request("GET", "nesil_documents", lookup)
        if not existing:
            raise SupabaseDataError("Belge kaydı oluşturulamadı veya bulunamadı.")
        return existing[0]

    def update_document_organization(self, document_id, folder_name, tags):
        if not isinstance(document_id, str) or not document_id or len(document_id) > 64:
            raise SupabaseDataError("Belge kimliği geçersiz.")
        if not isinstance(folder_name, str) or not folder_name.strip() or len(folder_name.strip()) > 80:
            raise SupabaseDataError("Klasör adı 1-80 karakter olmalı.")
        if not isinstance(tags, (list, tuple)) or len(tags) > 10:
            raise SupabaseDataError("En fazla 10 etiket kullanabilirsiniz.")
        clean_tags = []
        for tag in tags:
            if not isinstance(tag, str) or not tag.strip() or len(tag.strip()) > 30:
                raise SupabaseDataError("Etiketler 1-30 karakter olmalı.")
            clean_tags.append(tag.strip()[:30])
        q = urllib.parse.urlencode({"id": "eq." + document_id})
        self._request("PATCH", "nesil_documents", q, {
            "folder_name": folder_name.strip(),
            "tags": clean_tags,
            "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }, "return=minimal")

    def rename_document(self, document_id, current_name, new_name):
        if not isinstance(document_id, str) or not document_id or len(document_id) > 64:
            raise SupabaseDataError("Belge kimliği geçersiz.")
        if not isinstance(current_name, str) or not isinstance(new_name, str):
            raise SupabaseDataError("Dosya adı geçersiz.")
        new_name = new_name.strip()
        if not new_name or len(new_name) > 180 or "/" in new_name or "\\" in new_name:
            raise SupabaseDataError("Dosya adı 1-180 karakter olmalı ve yol içeremez.")
        current_ext = current_name.rsplit(".", 1)[-1].casefold() if "." in current_name else ""
        new_ext = new_name.rsplit(".", 1)[-1].casefold() if "." in new_name else ""
        if current_ext != new_ext:
            raise SupabaseDataError("Dosya uzantısı değiştirilemez.")
        q = urllib.parse.urlencode({"id": "eq." + document_id})
        self._request("PATCH", "nesil_documents", q, {
            "file_name": new_name,
            "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }, "return=minimal")

    def delete_document(self, document_id):
        if not isinstance(document_id, str) or not document_id or len(document_id) > 64:
            raise SupabaseDataError("Belge kimliği geçersiz.")
        q = urllib.parse.urlencode({"id": "eq." + document_id})
        self._request("DELETE", "nesil_documents", q, prefer="return=minimal")

    def list_memory(self, limit=50):
        q = urllib.parse.urlencode({"select": "id,memory_text,category,created_at,updated_at",
                                    "order": "updated_at.desc", "limit": str(max(1, min(int(limit), 100)))})
        return self._request("GET", "nesil_memory_items", q)

    def add_memory(self, memory_text, category="general"):
        if not isinstance(memory_text, str) or not memory_text.strip() or len(memory_text) > 4000:
            raise SupabaseDataError("Hafıza metni 1-4000 karakter olmalı.")
        q = urllib.parse.urlencode({"select": "id,memory_text,category,created_at,updated_at"})
        rows = self._request("POST", "nesil_memory_items", q,
                             {"user_id": self.user_id, "memory_text": memory_text.strip(), "category": (category or "general")[:40]},
                             "return=representation")
        if not rows:
            raise SupabaseDataError("Hafıza kaydedilemedi.")
        return rows[0]

    def update_memory(self, memory_id, memory_text):
        """Update one user's saved memory; RLS remains the ownership boundary."""
        if not isinstance(memory_id, str) or not memory_id or len(memory_id) > 64:
            raise SupabaseDataError("Hafıza kaydı kimliği geçersiz.")
        if not isinstance(memory_text, str) or not memory_text.strip() or len(memory_text) > 4000:
            raise SupabaseDataError("Hafıza metni 1-4000 karakter olmalı.")
        q = urllib.parse.urlencode({"id": "eq." + memory_id})
        payload = {
            "memory_text": memory_text.strip(),
            "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
        self._request("PATCH", "nesil_memory_items", q, payload, "return=minimal")

    def delete_memory(self, memory_id):
        q = urllib.parse.urlencode({"id": "eq." + str(memory_id)})
        self._request("DELETE", "nesil_memory_items", q, prefer="return=minimal")


def create_data_store(secrets, access_token, user_id):
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
    return SupabaseDataStore(setting("SUPABASE_URL"),
                              setting("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY"),
                              access_token, user_id)
