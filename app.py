"""Nesil AI: Streamlit assistant with optional persistent Supabase user data."""
import time
import json
import sqlite3
import streamlit as st
from file_reader import ALLOWED, MAX_FILES, MAX_TOTAL_BYTES, select_context, find_document_matches
from document_worker import extract_bounded, UploadData, load_saved_documents
from model_client import ask_model, read_api_key
from research_ui import show_research
from tools_ui import email_tools, voice_tools
from python_runner import runner_tools
from supabase_store import create_usage_store
from nesil_access_gate import require_access, is_admin_email
from supabase_auth import create_auth_client, SupabaseAuthError
from supabase_data import create_data_store, SupabaseDataError
from supabase_files import create_file_store, SupabaseFileError
from app_service import call_with_limits
from local_model import ask_local_model
from ui_theme import apply_theme
from dashboard_ui import show_dashboard_header, show_quick_actions, show_dashboard_rail


st.set_page_config(page_title="Nesil AI", page_icon="🤖", layout="wide")
apply_theme()
try:
    usage_store = create_usage_store()
    principal = require_access(st, usage_store)
    is_admin = is_admin_email(st.secrets, st.session_state.get('supabase_user_email'))
except (ValueError, OSError, sqlite3.Error):
    st.error("Giriş veya kullanım kaydı ayarları geçersiz. Yönetici yapılandırmayı kontrol etmeli.")
    st.stop()
defaults = {"messages": [], "documents": [], "file_names": [], "retry_at": 0,
            "last_request_at": 0, "pending_prompt": "", "last_error": "", "usage": {}, "upload_generation": 0, "note_generation": 0, "memory_input_generation": 0, "delete_confirmation_generation": 0}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Persistent user data uses the user's JWT; database RLS enforces ownership.
data_store = None
file_store = None
memory_context = ""
if principal != "public" and st.session_state.get("supabase_access_token"):
    auth_client = create_auth_client(st.secrets)
    try:
        data_store = create_data_store(st.secrets, st.session_state.supabase_access_token, principal)
        if not st.session_state.get("supabase_profile_loaded"):
            st.session_state.supabase_profile = data_store.get_profile()
            st.session_state.supabase_profile_loaded = True
        if not st.session_state.get("supabase_conversations_loaded"):
            st.session_state.supabase_conversations = data_store.list_conversations()
            st.session_state.supabase_conversations_loaded = True
        memories = data_store.list_memory()
        memory_context = "\n".join("- " + item["memory_text"] for item in memories)
        file_store = create_file_store(st.secrets, st.session_state.supabase_access_token, principal)
    except (SupabaseDataError, SupabaseFileError) as exc:
        if "süresi dolmuş" in str(exc).lower() and st.session_state.get("supabase_refresh_token"):
            try:
                refreshed = auth_client.refresh(st.session_state.supabase_refresh_token)
                st.session_state.supabase_access_token = refreshed["access_token"]
                st.session_state.supabase_refresh_token = refreshed["refresh_token"]
                data_store = create_data_store(st.secrets, refreshed["access_token"], principal)
                st.session_state.supabase_profile = data_store.get_profile()
                st.session_state.supabase_profile_loaded = True
                st.session_state.supabase_conversations = data_store.list_conversations()
                st.session_state.supabase_conversations_loaded = True
                memories = data_store.list_memory()
                memory_context = "\n".join("- " + item["memory_text"] for item in memories)
                file_store = create_file_store(st.secrets, refreshed["access_token"], principal)
            except (SupabaseAuthError, SupabaseDataError, SupabaseFileError, KeyError):
                st.session_state.pop("supabase_access_token", None)
                st.session_state.pop("supabase_refresh_token", None)
                st.session_state.pop("supabase_user_id", None)
                st.warning("Oturum yenilenemedi. Lütfen yeniden giriş yapın.")
                st.stop()
        else:
            st.warning(str(exc))

with st.sidebar:
    st.title("🤖 Nesil AI")
    st.caption("Türkçe yapay zekâ yardımcısı")
    st.caption("Genel sohbet ve diğer bulut modları Groq kullanır. Kodlama ve matematik modları yerel Ollama kullanır; otomatik bulut yedeği yoktur.")
    if data_store:
        with st.expander("👤 Profil ve hesap ayarları"):
            current_name = (st.session_state.get("supabase_profile") or {}).get("display_name", "")
            profile_name = st.text_input("Görünen ad", value=current_name, max_chars=80, key="profile_display_name")
            st.caption("Hesap e-postası: " + str(st.session_state.get("supabase_user_email", "")))
            if st.button("Profili kaydet", use_container_width=True):
                try:
                    updated_profile = data_store.update_profile(profile_name)
                    st.session_state.supabase_profile = updated_profile
                    st.success("Profil güncellendi.")
                except SupabaseDataError as exc:
                    st.error(str(exc))
    if is_admin:
        st.success("Yönetici hesabı")
        with st.expander("Yönetici hesabı bilgileri"):
            st.caption("Bu hesap Nesil AI yönetici listesinde tanımlı.")
            st.write("E-posta:", st.session_state.get("supabase_user_email", ""))
            st.caption("Yönetici yetkisi sunucu tarafındaki NESIL_ADMIN_EMAILS ayarıyla verilir.")
    elif principal != "public":
        st.caption("Standart kullanıcı hesabı")
    if principal != "public" and st.button("Çıkış yap", use_container_width=True):
        if st.session_state.get("supabase_access_token"):
            try:
                create_auth_client(st.secrets).sign_out(st.session_state.supabase_access_token)
            except SupabaseAuthError:
                pass
        st.session_state.clear()
        st.rerun()
    if data_store:
        st.subheader("💬 Kayıtlı sohbetler")
        if st.button("＋ Yeni sohbet", use_container_width=True):
            try:
                row = data_store.create_conversation()
                st.session_state.supabase_active_conversation = row["id"]
                st.session_state.messages = []
                st.session_state.pop("supabase_conversation_picker", None)
                st.session_state.supabase_conversations_loaded = False
                st.rerun()
            except SupabaseDataError as exc:
                st.error(str(exc))
        show_archived = st.checkbox("Arşivlenen sohbetleri göster", key="show_archived_conversations")
        if st.session_state.get("supabase_archived_view") != show_archived:
            try:
                st.session_state.supabase_conversations = data_store.list_conversations(include_archived=show_archived)
                st.session_state.supabase_archived_view = show_archived
            except SupabaseDataError as exc:
                st.warning(str(exc))
        conversations = st.session_state.get("supabase_conversations", [])
        if conversations:
            conversation_search = st.text_input("Sohbetlerde ara", placeholder="Başlığa göre filtrele…", key="conversation_search")
            if conversation_search.strip():
                needle = conversation_search.strip().casefold()
                conversations = [row for row in conversations if needle in str(row.get("title", "")).casefold()]
        if conversations:
            ids = [row["id"] for row in conversations]
            selected = st.session_state.get("supabase_active_conversation")
            if selected not in ids:
                selected = ids[0]
            selected_id = st.selectbox(
                "Sohbet geçmişi", ids, index=ids.index(selected),
                format_func=lambda value: next((row["title"] for row in conversations if row["id"] == value), "Sohbet"),
                key="supabase_conversation_picker",
            )
            if selected_id != st.session_state.get("supabase_active_conversation"):
                try:
                    rows = data_store.list_messages(selected_id)
                    st.session_state.messages = [{"role": row["role"], "content": row["content"]} for row in rows]
                    st.session_state.supabase_active_conversation = selected_id
                    st.rerun()
                except SupabaseDataError as exc:
                    st.error(str(exc))
            selected_row = next((row for row in conversations if row["id"] == selected_id), {})
            flag_col1, flag_col2 = st.columns(2)
            is_pinned = bool(selected_row.get("is_pinned", False))
            is_archived = bool(selected_row.get("is_archived", False))
            if flag_col1.button("📌 Sabitle" if not is_pinned else "Sabitlemeyi kaldır", use_container_width=True):
                try:
                    data_store.pin_conversation(selected_id, not is_pinned)
                    st.session_state.supabase_conversations_loaded = False
                    st.rerun()
                except SupabaseDataError as exc:
                    st.error(str(exc))
            if flag_col2.button("Arşivden çıkar" if is_archived else "Arşivle", use_container_width=True):
                try:
                    data_store.archive_conversation(selected_id, not is_archived)
                    st.session_state.supabase_conversations_loaded = False
                    st.session_state.supabase_archived_view = None
                    st.rerun()
                except SupabaseDataError as exc:
                    st.error(str(exc))
            with st.expander("✏️ Sohbet başlığını düzenle"):
                current_title = next((row.get("title", "") for row in conversations if row["id"] == selected_id), "")
                renamed_title = st.text_input("Yeni başlık", value=current_title, max_chars=120, key="rename_conversation_title")
                if st.button("Başlığı kaydet", use_container_width=True):
                    try:
                        data_store.update_conversation_title(selected_id, renamed_title)
                        st.session_state.supabase_conversations_loaded = False
                        st.success("Sohbet başlığı güncellendi.")
                        st.rerun()
                    except SupabaseDataError as exc:
                        st.error(str(exc))
            st.caption("Seçili sohbeti ve içindeki mesajları kalıcı olarak silmek için aşağıyı kullanın.")
            confirm_delete = st.checkbox("Seçili sohbeti silmeyi onaylıyorum", key=f"confirm_delete_conversation_{st.session_state.delete_confirmation_generation}")
            if st.button("🗑️ Seçili sohbeti sil", disabled=not confirm_delete, use_container_width=True):
                try:
                    data_store.delete_conversation(selected_id)
                    st.session_state.messages = []
                    st.session_state.pop("supabase_active_conversation", None)
                    st.session_state.pop("supabase_conversation_picker", None)
                    st.session_state.supabase_conversations_loaded = False
                    st.session_state.delete_confirmation_generation += 1
                    st.success("Sohbet silindi.")
                    st.rerun()
                except SupabaseDataError as exc:
                    st.error(str(exc))
        st.subheader("🧠 Kalıcı hafıza")
        memory_text = st.text_area("Hatırlanmasını istediğiniz bilgi", max_chars=4000, key=f"memory_input_{st.session_state.memory_input_generation}")
        if st.button("Hafızaya kaydet", use_container_width=True):
            try:
                data_store.add_memory(memory_text)
                st.session_state.memory_input_generation += 1
                st.rerun()
            except SupabaseDataError as exc:
                st.error(str(exc))
        try:
            for item in data_store.list_memory():
                with st.expander(item["memory_text"][:70] or "Hafıza kaydı"):
                    edited_memory = st.text_area(
                        "Hafıza metni", value=item["memory_text"], max_chars=4000,
                        key="edit_memory_text_" + item["id"],
                    )
                    col1, col2 = st.columns(2)
                    if col1.button("Değişiklikleri kaydet", key="save_memory_" + item["id"], use_container_width=True):
                        try:
                            data_store.update_memory(item["id"], edited_memory)
                            st.success("Hafıza kaydı güncellendi.")
                            st.rerun()
                        except SupabaseDataError as exc:
                            st.error(str(exc))
                    if col2.button("Hafızayı sil", key="delete_memory_" + item["id"], use_container_width=True):
                        try:
                            data_store.delete_memory(item["id"])
                            st.rerun()
                        except SupabaseDataError as exc:
                            st.error(str(exc))
        except SupabaseDataError as exc:
            st.warning(str(exc))
    mode = st.selectbox("Çalışma biçimi", ["Genel yardımcı", "Görev planlama", "Kodlama yardımcısı", "Matematik öğretmeni", "Belge ve rapor yardımcısı"])
    note = st.text_area("Sohbet notu", max_chars=2000, key=f"note_{st.session_state.note_generation}", help="Amaç, tercihler ve önemli kararlar. Her soruda modele gönderilir; sohbet temizlenince silinir.")
    if memory_context:
        note = (note + "\n\nKULLANICININ KAYITLI HAFIZASI (yalnızca bağlam):\n" + memory_context)[:6000]
    if file_store and data_store:
        st.subheader("🗂️ Özel belge kitaplığım")
        library_search = st.text_input("Belgelerde ara", placeholder="Dosya adına göre ara…", max_chars=100, key="library_search")
        try:
            all_docs = data_store.list_documents(limit=100)
            folders = sorted({row.get("folder_name", "Genel") for row in all_docs if row.get("folder_name")})
            folder_options = ["Tüm klasörler"] + folders
            selected_folder = st.selectbox("Klasör", folder_options, key="library_folder_filter")
            docs = data_store.list_documents(
                search=library_search,
                folder="" if selected_folder == "Tüm klasörler" else selected_folder,
                limit=100,
            )
            if not docs:
                st.caption("Bu aramada belge bulunamadı.")
            else:
                st.caption(f"{len(docs)} kayıt listeleniyor. Tek seferde en fazla 5 dosya ve toplam 20 MB analiz alanına alınır.")
                if st.button("📚 Bu listedeki belgeleri topluca analiz alanına yükle", use_container_width=True, key="load_saved_document_batch"):
                    try:
                        with st.spinner("Belgeler indiriliyor ve okunuyor…"):
                            batch_loaded, batch_skipped = load_saved_documents(file_store, docs)
                        st.session_state.documents = batch_loaded
                        st.session_state.file_names = [item.name for item in batch_loaded]
                        st.session_state.saved_document_load_skipped = batch_skipped
                        st.rerun()
                    except Exception:
                        st.warning("Belge grubu yüklenemedi. Dosya erişimini ve bağlantıyı kontrol edin.")
                skipped = st.session_state.get("saved_document_load_skipped", [])
                if skipped:
                    with st.expander(f"Yüklenemeyen/atlanmış dosyalar ({len(skipped)})"):
                        for skipped_name, reason in skipped:
                            st.caption(f"{skipped_name}: {reason}")
            for saved in docs:
                object_path = saved["object_path"]
                title = saved["file_name"]
                with st.expander(title + " · " + saved.get("folder_name", "Genel")):
                    st.caption(f"{saved.get('file_size', 0) // 1024} KB · {saved.get('content_type', 'dosya')}")
                    cached_download = st.session_state.get("saved_file_download")
                    if cached_download and cached_download.get("path") == object_path:
                        st.download_button("Dosyayı indir", cached_download["data"], file_name=title,
                                           key="download_saved_" + saved["id"])
                    if st.button("İndirmeyi hazırla", key="prepare_download_" + saved["id"]):
                        try:
                            with st.spinner("Dosya hazırlanıyor…"):
                                data = file_store.download(object_path)
                            st.session_state.saved_file_download = {"path": object_path, "data": data}
                            st.rerun()
                        except SupabaseFileError as exc:
                            st.warning(str(exc))
                    if st.button("Belge analiz alanına al", key="analyze_saved_" + saved["id"]):
                        try:
                            with st.spinner("Kayıtlı belge okunuyor…"):
                                file_bytes = file_store.download(object_path)
                                extracted = extract_bounded(UploadData(title, file_bytes))
                            st.session_state.documents = [item for item in st.session_state.documents if item.name != title]
                            st.session_state.documents.append(extracted)
                            st.session_state.file_names = [item.name for item in st.session_state.documents if item.text]
                            if extracted.text:
                                st.success("Belge analiz alanına eklendi.")
                            else:
                                st.warning(extracted.scope)
                            st.rerun()
                        except SupabaseFileError as exc:
                            st.warning(str(exc))
                    new_folder = st.text_input("Klasör adı", value=saved.get("folder_name") or "Genel",
                                               max_chars=80, key="folder_" + saved["id"])
                    new_tags = st.text_input("Etiketler (virgülle ayırın)",
                                             value=", ".join(saved.get("tags") or []), max_chars=310,
                                             key="tags_" + saved["id"])
                    if st.button("Klasör ve etiketleri kaydet", key="save_doc_meta_" + saved["id"]):
                        try:
                            tags = [tag.strip() for tag in new_tags.split(",") if tag.strip()]
                            data_store.update_document_organization(saved["id"], new_folder, tags)
                            st.success("Belge bilgileri güncellendi.")
                            st.rerun()
                        except SupabaseDataError as exc:
                            st.error(str(exc))
                    if st.button("Kitaplıktan sil", key="delete_saved_" + saved["id"]):
                        try:
                            file_store.delete(object_path)
                            data_store.delete_document(saved["id"])
                            if st.session_state.get("saved_file_download", {}).get("path") == object_path:
                                st.session_state.pop("saved_file_download", None)
                            st.rerun()
                        except (SupabaseFileError, SupabaseDataError) as exc:
                            st.warning(str(exc))
        except SupabaseDataError as exc:
            st.warning("Belge kataloğu hazır değil. Gerekli Supabase migration henüz uygulanmamış olabilir: " + str(exc))
        except SupabaseFileError as exc:
            st.warning("Özel belge kitaplığı hazır değil: " + str(exc))
    st.divider()
    if st.session_state.documents:
        st.subheader("🔎 Açık belgelerde içerik ara")
        document_query = st.text_input("Belge içeriğinde ara", max_chars=200, placeholder="Örn. toplam tutar, sözleşme tarihi…", key="document_content_search")
        if document_query.strip():
            matches = []
            for document in st.session_state.documents:
                for match in find_document_matches(document.text, document_query, max_results=8):
                    matches.append((document.name, match))
            matches.sort(key=lambda item: (-item[1]["score"], item[0], item[1]["line"]))
            if matches:
                st.caption(f"{len(matches)} eşleşme bulundu. Sonuçlar mevcut oturumdaki çıkarılmış metin içinde aranır.")
                for file_name, match in matches[:30]:
                    st.markdown(f"**{file_name} · {match['location']} · metin satırı {match['line']}**")
                    st.write(match["excerpt"])
            else:
                st.info("Açık belgelerde bu ifadeyle eşleşme bulunamadı.")
    st.subheader("📎 Dosya analizi")
    st.caption("En fazla 5 dosya, dosya başına 10 MB, toplam 20 MB. Belgelerin sınırlı metin kesitleri analiz edilir.")
    uploads = st.file_uploader("Dosya seçin", type=list(ALLOWED), accept_multiple_files=True, key=f"uploads_{st.session_state.upload_generation}")
    ocr_enabled = st.checkbox("Taranmış PDF için yerel OCR kullan", value=False, help="Sunucuda OCR paketleri ve Tesseract gerekir. İlk 20 taranmış sayfaya kadar denenir; sonuçları kontrol edin.")
    st.caption("Dosya kesitleri seçili modun sağlayıcısına gönderilir: yerel modlarda Ollama'ya, diğer modlarda Groq'a. Hassas verileri yüklemeyin.")
    if st.button("Seçilen dosyaları oku", disabled=not uploads, use_container_width=True):
        if len(uploads) > MAX_FILES or sum(up.size for up in uploads) > MAX_TOTAL_BYTES:
            st.error("En fazla 5 dosya ve toplam 20 MB yükleyebilirsiniz. Önceki dosya bağlamı korunuyor.")
        else:
            with st.spinner("Dosyalar okunuyor…"):
                results = [extract_bounded(up, ocr=ocr_enabled) for up in uploads]
            st.session_state.documents = results
            st.session_state.file_names = [r.name for r in results if r.text]
            count = sum(bool(r.text) for r in results)
            if count:
                st.success(f"{len(results)} dosyadan {count} tanesinde metin bulundu.")
            else:
                st.warning("Dosyalardan analiz edilebilir metin çıkarılamadı.")
    if file_store and uploads and st.button("Seçilen dosyaları özel kitaplığıma kaydet", use_container_width=True):
        if len(uploads) > MAX_FILES or sum(upload.size for upload in uploads) > MAX_TOTAL_BYTES:
            st.error("Özel kitaplık için de en fazla 5 dosya ve toplam 20 MB sınırı geçerlidir.")
        else:
            try:
                saved_count = 0
                for upload in uploads:
                    stored = file_store.upload(upload.name, upload.getvalue())
                    try:
                        data_store.add_document(stored["path"], stored["name"], stored["size"], stored["content_type"])
                    except SupabaseDataError:
                        file_store.delete(stored["path"])
                        raise
                    saved_count += 1
                st.success(f"{saved_count} dosya özel kitaplığınıza kaydedildi.")
                st.rerun()
            except (SupabaseFileError, SupabaseDataError) as exc:
                st.error(f"{saved_count} dosya kaydedildi; kalan dosyalar kaydedilemedi: {exc}")
    for result in st.session_state.documents:
        with st.expander(f"{result.name} — {result.status}"):
            st.write(result.scope)
    if st.session_state.documents and st.button("Dosya bağlamını kaldır", use_container_width=True):
        st.session_state.documents = []
        st.session_state.file_names = []
        st.rerun()
    st.divider()
    local_mode = mode in ("Kodlama yardımcısı", "Matematik öğretmeni")
    web_enabled = st.checkbox("İnternette araştır", value=False, disabled=local_mode)
    st.caption("İnternet araştırması yalnızca Groq modlarında kullanılabilir. Yerel Ollama modlarında ağ araştırması yapılmaz.")
    email_tools(st)
    st.divider()
    if st.button("Sohbeti temizle", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pop("supabase_active_conversation", None)
        st.session_state.pop("supabase_conversation_picker", None)
        st.session_state.pending_prompt = ""
        st.session_state.last_error = ""
        st.session_state.pop("source_review", None)
        st.session_state.note_generation += 1
        st.session_state.draft_generation = st.session_state.get("draft_generation", 0) + 1
        st.session_state.pop("prepared_draft", None)
        st.session_state.pop("draft_notice", None)
        st.session_state.pop("draft_fields", None)
        st.session_state.python_mini_enabled = False
        st.rerun()
    if st.button("Tüm oturum içeriğini temizle", use_container_width=True):
        # This clears this session only; saved database records remain available.
        st.session_state.pop("supabase_active_conversation", None)
        st.session_state.pop("supabase_conversation_picker", None)
        # Rate-limit timers survive content deletion.
        for key in ("messages", "documents", "file_names", "pending_prompt", "last_error", "usage"):
            st.session_state.pop(key, None)
        st.session_state.pop("source_review", None)
        st.session_state.upload_generation += 1
        st.session_state.note_generation += 1
        st.session_state.draft_generation = st.session_state.get("draft_generation", 0) + 1
        st.session_state.pop("prepared_draft", None)
        st.session_state.pop("draft_notice", None)
        st.session_state.pop("draft_fields", None)
        st.session_state.python_mini_enabled = False
        st.rerun()
    if st.session_state.messages:
        transcript = "\n\n".join(("KULLANICI: " if m["role"] == "user" else "NESİL AI: ") + m["content"] for m in st.session_state.messages)
        st.download_button("Sohbeti TXT olarak indir", transcript, file_name="nesil_ai_sohbet.txt", mime="text/plain", use_container_width=True)
        records = [m["research"] for m in st.session_state.messages if (m.get("research") or {}).get("requested")]
        if records:
            st.download_button("Kaynak kayıtlarını indir", json.dumps(records, ensure_ascii=False, indent=2), file_name="nesil_ai_kaynaklar.json", mime="application/json")
    st.caption("Sistem komutu, e-posta gönderimi ve bilgisayar kontrolü yoktur. Python Mini kodları yalnızca tarayıcıdaki ayrı çalışma alanında çalışır.")

st.markdown('<div class="nd-viewport-spacer" aria-hidden="true"></div>', unsafe_allow_html=True)
main_col, rail_col = st.columns([3.05, 1.05], gap='medium')
with main_col:
    profile_name = ((st.session_state.get("supabase_profile") or {}).get("display_name") or "").strip()
    account_email = st.session_state.get("supabase_user_email", "")
    account_handle = account_email.split("@", 1)[0].replace(".", " ").replace("_", " ").replace("-", " ").strip().title()
    display_name = profile_name or account_handle or "Hoş geldiniz"
    provider_label = "Ollama (Yerel)" if mode in ("Kodlama yardımcısı", "Matematik öğretmeni") else "Groq"
    mode_label = "Yönetici" if is_admin else "Standart Ücretsiz" if principal != "public" else "Misafir"
    show_dashboard_header(display_name, provider_label, mode_label)
    show_quick_actions()
    if st.session_state.file_names:
        st.info("Dosya kesitleri hazır: " + ", ".join(st.session_state.file_names))
    if not st.session_state.messages:
        st.markdown(
            '<div class="nd-chat-welcome"><div class="nd-chat-bubble">◌</div><div><strong>Yeni Sohbet</strong>'
            '<p>Nesil AI ile görüşmeye başlayın. Aşağıdaki örneklerden birini seçebilirsiniz.</p></div></div>',
            unsafe_allow_html=True,
        )
        prompts = [
            ("📄", "Bu belgeyi özetle.", "Yüklediğim belgeyi ana başlıkları ve önemli noktalarıyla özetle."),
            ("🔎", "Güncel bir konuda araştırma yap.", "Bu konuda güncel ve güvenilir kaynaklarla araştırma yap."),
            ("📊", "Excel dosyasını analiz et.", "Yüklediğim Excel dosyasını analiz et ve önemli bulguları açıkla."),
            ("💡", "Bir plan hazırla.", "Hedefime ulaşmak için uygulanabilir, adım adım bir plan hazırla."),
        ]
        for row_start in (0, 2):
            sample_cols = st.columns(2, gap="small")
            for sample_col, (symbol, label_text, question) in zip(sample_cols, prompts[row_start:row_start + 2]):
                with sample_col:
                    if st.button(symbol + "  " + label_text, key="sample_" + label_text, use_container_width=True):
                        st.session_state.dashboard_quick_prompt = question
                        st.rerun()
    for message_index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                show_research(st, message, message_index)
    voice_tools(st)
    runner_tools(st)
    wait = max(0, int(st.session_state.retry_at - time.time() + 0.999))
    if wait:
        st.warning(f"Sağlayıcı bekleme süresi: yaklaşık {wait} saniye. Süre dolunca yeniden deneyin.")
    if st.session_state.last_error:
        st.error(st.session_state.last_error)
    retry = False
    if st.session_state.pending_prompt:
        with st.expander("Gönderilemeyen sorunuz", expanded=True):
            st.write(st.session_state.pending_prompt)
        retry = st.button("Soruyu yeniden dene")
    prompt = st.chat_input("Mesajınızı buraya yazın…")
    if st.session_state.get("dashboard_quick_prompt") and not prompt:
        prompt = st.session_state.pop("dashboard_quick_prompt")
    if retry and not prompt:
        prompt = st.session_state.pending_prompt
    review = st.session_state.get("source_review")
    if review and review.pop("queued", False) and not prompt:
        prompt = review["prompt"]
    if prompt:
        if len(prompt) <= 12000:
            st.session_state.pending_prompt = prompt
        now = time.time()
        if now < st.session_state.retry_at:
            st.warning("Sağlayıcının bekleme süresi henüz dolmadı. API isteği gönderilmedi.")
        elif now - st.session_state.last_request_at < 5:
            st.warning("İki gönderim arasında en az 5 saniye bekleyin. API isteği gönderilmedi.")
        elif len(prompt) > 12000:
            st.warning("Lütfen soruyu 12.000 karakterden kısa bölümlere ayırın.")
        else:
            st.session_state.last_request_at = now
            st.session_state.pending_prompt = prompt
            last_question = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"), "")
            retrieval_query = prompt + (" " + last_question if len(prompt.split()) < 6 else "")
            context = select_context(st.session_state.documents, retrieval_query, limit=10000)
            reviewing = bool(review and prompt == review["prompt"])
            if reviewing:
                context = review["context"]
            request_web = web_enabled and not reviewing and mode not in ("Kodlama yardımcısı", "Matematik öğretmeni")
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                local_mode = mode in ("Kodlama yardımcısı", "Matematik öğretmeni")
                label = "Kaynaklı araştırma yanıtı hazırlanıyor…" if request_web else "Yerel model yanıt hazırlıyor…" if local_mode else "Yanıt hazırlanıyor…"
                with st.spinner(label):
                    history = [] if reviewing else st.session_state.messages
                    if local_mode:
                        result = ask_local_model(prompt, mode, history, context, note="" if reviewing else note)
                    else:
                        result = call_with_limits(
                            ask_model, usage_store, principal, prompt, mode,
                            history, context, request_web, api_key=read_api_key(st.secrets),
                            note="" if reviewing else note,
                        )
                st.markdown(result.text)
                if result.ok:
                    show_research(st, {"research": result.research, "research_requested": request_web}, len(st.session_state.messages))
            if result.ok:
                if data_store:
                    try:
                        active_id = st.session_state.get("supabase_active_conversation")
                        if not active_id:
                            title = prompt.strip().replace("\n", " ")[:70] or "Yeni sohbet"
                            active_id = data_store.create_conversation(title)["id"]
                            st.session_state.supabase_active_conversation = active_id
                        data_store.add_message(active_id, "user", prompt)
                        data_store.add_message(active_id, "assistant", result.text)
                        data_store.touch_conversation(active_id)
                        if len(st.session_state.messages) == 0:
                            data_store.update_conversation_title(active_id, prompt.strip().replace("\n", " ")[:70] or "Yeni sohbet")
                        st.session_state.supabase_conversations_loaded = False
                    except SupabaseDataError as exc:
                        st.warning("Yanıt üretildi ancak sohbet veritabanına kaydedilemedi: " + str(exc))
                st.session_state.messages.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": result.text, "research_requested": request_web, "research": result.research}])
                # Bound server memory. Provider receives a smaller whole-message window.
                st.session_state.messages = st.session_state.messages[-100:]
                st.session_state.pending_prompt = ""
                st.session_state.last_error = ""
                st.session_state.usage = result.usage or {}
                st.session_state.pop("source_review", None)
                st.rerun()
            else:
                st.session_state.last_error = result.text
                if result.retry_after:
                    st.session_state.retry_at = time.time() + result.retry_after
    st.caption("Nesil AI · Yanıtları ve kaynakları önemli kararlar öncesinde doğrulayın. Sohbet oturumda en fazla son 100 mesajı tutar; model bağlamına sığmayan eski mesajlar gönderilmez.")
    
    
with rail_col:
    show_dashboard_rail(data_store, SupabaseDataError)
