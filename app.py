"""Nesil AI: session-only Streamlit chat."""
import time
import json
import sqlite3
import streamlit as st
from file_reader import ALLOWED, MAX_FILES, MAX_TOTAL_BYTES, select_context
from document_worker import extract_bounded
from model_client import ask_model, read_api_key
from research_ui import show_research
from tools_ui import email_tools, voice_tools
from python_runner import runner_tools
from supabase_store import create_usage_store
from access_control import require_access
from supabase_auth import create_auth_client, SupabaseAuthError
from supabase_data import create_data_store, SupabaseDataError
from app_service import call_with_limits
from local_model import ask_local_model


def _is_admin_email(secrets, email):
    """Check the server-side administrator allowlist without importing another module symbol."""
    configured = secrets.get("NESIL_ADMIN_EMAILS", [])
    if isinstance(configured, str):
        configured = configured.replace(";", ",").split(",")
    if not isinstance(configured, (list, tuple, set)):
        return False
    allowed = {str(item).strip().lower() for item in configured if str(item).strip()}
    return str(email or "").strip().lower() in allowed


st.set_page_config(page_title="Nesil AI", page_icon="🤖", layout="wide")
try:
    usage_store = create_usage_store()
    principal = require_access(st, usage_store)
    is_admin = bool(st.session_state.get('supabase_user_email') and _is_admin_email(
        st.secrets, st.session_state.get('supabase_user_email')
    ))
except (ValueError, OSError, sqlite3.Error):
    st.error("Giriş veya kullanım kaydı ayarları geçersiz. Yönetici yapılandırmayı kontrol etmeli.")
    st.stop()
defaults = {"messages": [], "documents": [], "file_names": [], "retry_at": 0,
            "last_request_at": 0, "pending_prompt": "", "last_error": "", "usage": {}, "upload_generation": 0, "note_generation": 0, "memory_input_generation": 0}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Persistent user data uses the user's JWT; database RLS enforces ownership.
data_store = None
memory_context = ""
if principal != "public" and st.session_state.get("supabase_access_token"):
    auth_client = create_auth_client(st.secrets)
    try:
        data_store = create_data_store(st.secrets, st.session_state.supabase_access_token, principal)
        if not st.session_state.get("supabase_conversations_loaded"):
            st.session_state.supabase_conversations = data_store.list_conversations()
            st.session_state.supabase_conversations_loaded = True
        memories = data_store.list_memory()
        memory_context = "\n".join("- " + item["memory_text"] for item in memories)
    except SupabaseDataError as exc:
        if "süresi dolmuş" in str(exc).lower() and st.session_state.get("supabase_refresh_token"):
            try:
                refreshed = auth_client.refresh(st.session_state.supabase_refresh_token)
                st.session_state.supabase_access_token = refreshed["access_token"]
                st.session_state.supabase_refresh_token = refreshed["refresh_token"]
                data_store = create_data_store(st.secrets, refreshed["access_token"], principal)
                st.session_state.supabase_conversations = data_store.list_conversations()
                st.session_state.supabase_conversations_loaded = True
                memories = data_store.list_memory()
                memory_context = "\n".join("- " + item["memory_text"] for item in memories)
            except (SupabaseAuthError, SupabaseDataError, KeyError):
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
                st.session_state.supabase_conversations_loaded = False
                st.rerun()
            except SupabaseDataError as exc:
                st.error(str(exc))
        conversations = st.session_state.get("supabase_conversations", [])
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
            st.caption("Seçili sohbeti ve içindeki mesajları kalıcı olarak silmek için aşağıyı kullanın.")
            confirm_delete = st.checkbox("Seçili sohbeti silmeyi onaylıyorum", key="confirm_delete_conversation")
            if st.button("🗑️ Seçili sohbeti sil", disabled=not confirm_delete, use_container_width=True):
                try:
                    data_store.delete_conversation(selected_id)
                    st.session_state.messages = []
                    st.session_state.pop("supabase_active_conversation", None)
                    st.session_state.supabase_conversations_loaded = False
                    st.session_state.pop("confirm_delete_conversation", None)
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
                col1, col2 = st.columns([5, 1])
                col1.caption(item["memory_text"])
                if col2.button("Sil", key="delete_memory_" + item["id"]):
                    data_store.delete_memory(item["id"])
                    st.rerun()
        except SupabaseDataError as exc:
            st.warning(str(exc))
    mode = st.selectbox("Çalışma biçimi", ["Genel yardımcı", "Görev planlama", "Kodlama yardımcısı", "Matematik öğretmeni", "Belge ve rapor yardımcısı"])
    note = st.text_area("Sohbet notu", max_chars=2000, key=f"note_{st.session_state.note_generation}", help="Amaç, tercihler ve önemli kararlar. Her soruda modele gönderilir; sohbet temizlenince silinir.")
    if memory_context:
        note = (note + "\n\nKULLANICININ KAYITLI HAFIZASI (yalnızca bağlam):\n" + memory_context)[:6000]
    st.divider()
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

st.title("🤖 Nesil AI")
st.caption("Sohbet et, belgeleri incele, kaynaklarıyla araştır.")
if st.session_state.file_names:
    st.info("Dosya kesitleri hazır: " + ", ".join(st.session_state.file_names))
if not st.session_state.messages:
    st.markdown("**Örnek görevler**\n- Bir iş sürecini adım adım planla.\n- Yüklediğim belgenin önemli noktalarını açıkla.\n- Araştırmayı açarak güncel bilgileri kaynaklarıyla karşılaştır.")
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
prompt = st.chat_input("Görevini buraya yaz…")
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

