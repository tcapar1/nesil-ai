"""Reference-matched dashboard components for Nesil AI."""
import html
import streamlit as st


def show_dashboard_header(display_name, provider_label, mode_label):
    name = html.escape((display_name or "").strip() or "Hoş geldiniz")
    st.markdown(
        """
        <div class="nd-topbar">
          <div class="nd-brand"><div class="nd-logo">🤖</div><div><strong>Nesil AI</strong>
          <span>Sohbet et, belgeleri incele, araştır, üret.</span></div></div>
          <div class="nd-models">
            <div class="nd-model nd-model-primary"><b>ϟ</b><span><strong>{html.escape(provider_label)}</strong><small>Aktif model sağlayıcısı</small></span></div>
            <div class="nd-model nd-model-secure"><b>✓</b><span><strong>Güvenli Alan</strong><small>Kişisel çalışma alanınız</small></span></div>
          </div>
          <div class="nd-account"><div class="nd-avatar">""" + (name[:1].upper() if name else "N") + """</div>
            <div><strong>""" + name + """</strong><small>""" + html.escape(mode_label) + """</small></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <section class="nd-hero">
          <div class="nd-hero-copy">
            <div class="nd-eyebrow">KİŞİSEL YAPAY ZEKÂ ÇALIŞMA ALANINIZ</div>
            <h1>Merhaba, """ + name + """ 👋</h1>
            <p>Nesil AI; belgelerinizi analiz edebilir, internette araştırma yapabilir,
            sorularınızı yanıtlayabilir ve günlük işlerinize yardımcı olabilir.</p>
            <div class="nd-hero-tags"><span>✦ Türkçe yapay zekâ</span><span>▤ Belge analizi</span><span>⌕ Kaynaklı araştırma</span></div>
          </div>
          <div class="nd-robot-scene" aria-hidden="true">
            <div class="nd-orbit"></div><div class="nd-float nd-float-doc">▤</div>
            <div class="nd-float nd-float-chart">▥</div><div class="nd-float nd-float-web">◎</div>
            <div class="nd-robot"><div class="nd-antenna"></div><div class="nd-robot-face"><i></i><i></i></div><div class="nd-robot-mouth"></div></div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def show_quick_actions():
    cards = [
        ("📄", "Belge Analizi", "PDF, Word, Excel ve daha fazlasını analiz et", "Yüklediğim belgeyi ana başlıkları ve önemli noktalarıyla özetle."),
        ("🌐", "İnternette Araştır", "Güncel bilgilere kaynaklarıyla ulaş", "Bu konuda güncel ve güvenilir kaynaklarla araştırma yap."),
        ("🧠", "Kalıcı Hafıza", "Önemli bilgileri hatırla", "Kayıtlı hafızamı ve bu sohbetteki önemli bilgileri dikkate al."),
        ("🗂️", "Özel Belge Kitaplığım", "Dosyalarını güvenle sakla", "Özel belge kitaplığımdaki dosyaları bulmama yardımcı ol."),
    ]
    cols = st.columns(4, gap="small")
    for col, (icon, title, caption, prompt) in zip(cols, cards):
        with col:
            st.markdown(
                f'<div class="nd-feature"><div class="nd-feature-icon">{icon}</div>'
                f'<div><strong>{title}</strong><small>{caption}</small></div><span class="nd-arrow">→</span></div>',
                unsafe_allow_html=True,
            )
            if st.button("Aç", key="feature_" + title, use_container_width=True):
                st.session_state.dashboard_quick_prompt = prompt
                st.rerun()


def show_dashboard_rail(data_store, data_error_type):
    with st.container():
        st.markdown('<div class="nd-rail-heading"><strong>Son Belgelerim</strong><span>Hesabınıza özel</span></div>', unsafe_allow_html=True)
        docs = []
        if data_store:
            try:
                docs = data_store.list_documents(limit=5)
            except data_error_type:
                docs = []
        if docs:
            for item in docs:
                filename = html.escape(str(item.get("file_name") or "Belge"))
                ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else "DOC"
                icon = "📕" if ext == "PDF" else "📗" if ext in ("XLS", "XLSX", "CSV") else "📘" if ext in ("DOC", "DOCX") else "📄"
                size = int(item.get("file_size") or 0)
                st.markdown(
                    f'<div class="nd-rail-item"><span class="nd-file-icon">{icon}</span><div><strong>{filename}</strong>'
                    f'<small>{ext} · {size/1024:.1f} KB</small></div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Henüz kayıtlı belge yok.")
    st.divider()
    with st.container():
        st.markdown('<div class="nd-rail-heading"><strong>Kayıtlı Sohbetler</strong><span>Son görüşmeler</span></div>', unsafe_allow_html=True)
        chats = st.session_state.get("supabase_conversations", []) if data_store else []
        if chats:
            for item in chats[:6]:
                title = html.escape(str(item.get("title") or "Yeni sohbet"))
                st.markdown(f'<div class="nd-chat-item"><span>◌</span><div><strong>{title}</strong><small>Kişisel sohbet geçmişiniz</small></div></div>', unsafe_allow_html=True)
        else:
            st.caption("Kayıtlı sohbetleriniz burada listelenir.")
