"""Dashboard layout helpers for Nesil AI."""
import streamlit as st


def show_dashboard_header(display_name, provider_label):
    name = (display_name or "").strip() or "Hoş geldiniz"
    st.markdown("### ✨ Nesil AI")
    st.caption("Sohbet et, belgeleri incele, araştır, üret.")
    with st.container(border=True):
        st.markdown("## Merhaba, " + name + " 👋")
        st.write("Belgelerinizi analiz edin, fikirlerinizi geliştirin, araştırmalarınızı tek bir yerden yönetin.")
        st.caption("✦ Türkçe asistan　 ·　 ▣ Belge analizi　 ·　 ⌕ Kaynaklı araştırma")
    st.caption("● " + provider_label + "　 ·　 🔒 Hesabınıza özel alan　 ·　 ⚡ Ücretsiz kullanım öncelikli")


def show_quick_actions():
    columns = st.columns(4)
    prompts = [
        ("▤", "Belgeyi özetle", "Yüklediğim belgeyi ana başlıkları ve önemli noktalarıyla özetle."),
        ("⌕", "Araştırma yap", "Bu konuda güncel ve güvenilir kaynaklarla araştırma yap."),
        ("▦", "Excel'i incele", "Yüklediğim Excel dosyasını incele; sayfaları, sütunları ve önemli bulguları açıkla."),
        ("✦", "Plan hazırla", "Hedefime ulaşmak için uygulanabilir, adım adım bir plan hazırla."),
    ]
    for col, (symbol, title, prompt) in zip(columns, prompts):
        with col:
            with st.container(border=True):
                st.markdown("### " + symbol + " " + title)
                st.caption("Hızlı başlangıç")
                if st.button("Başlat", key="quick_" + title, use_container_width=True):
                    st.session_state.dashboard_quick_prompt = prompt
                    st.rerun()


def show_dashboard_rail(data_store, data_error_type):
    with st.container(border=True):
        st.markdown("### Son Belgeler")
        docs = []
        if data_store:
            try:
                docs = data_store.list_documents(limit=5)
            except data_error_type:
                docs = []
        if docs:
            for item in docs:
                st.markdown("**▤ " + str(item.get("file_name") or "Belge") + "**")
                st.caption(str(item.get("folder_name") or "Genel") + " · " + str(int(item.get("file_size") or 0) // 1024) + " KB")
        else:
            st.caption("Henüz kayıtlı belge yok.")
    with st.container(border=True):
        st.markdown("### Kayıtlı Sohbetler")
        chats = st.session_state.get("supabase_conversations", []) if data_store else []
        if chats:
            for item in chats[:6]:
                st.markdown("◌ " + str(item.get("title") or "Yeni sohbet"))
        else:
            st.caption("Kayıtlı sohbetleriniz burada listelenir.")
