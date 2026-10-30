"""Optional tools: no model calls and no account access."""
from email_draft import MAX_BODY, build_draft
from voice import render_speech


def email_tools(st):
    state = st.session_state
    if "draft_generation" not in state:
        state.draft_generation = 0
    generation = state.draft_generation
    with st.expander("✉️ E-posta taslağı"):
        st.caption("Bu araç e-posta göndermez veya hesabına bağlanmaz. Taslak alanları modele gönderilmez.")
        prepared = state.get("prepared_draft")
        if prepared:
            recipient, subject, body = prepared["fields"]
            st.success("Taslak hazır; hiçbir e-posta gönderilmedi.")
            st.write("Alıcı: " + (recipient.strip() or "henüz seçilmedi"))
            st.write("Konu: " + subject.strip())
            st.caption("Hazırlanan ileti")
            with st.container(height=180):
                st.text(body)
            st.download_button("E-posta taslağını indir (.eml)", prepared["content"],
                               file_name="nesil_ai_taslak.eml", mime="message/rfc822")
            st.caption("Dosyayı destekleyen e-posta programında açıp kontrol ederek kendin gönderebilirsin. Taslak olarak açılma davranışı programa göre değişir.")
            if st.button("Taslağı düzenle"):
                state.draft_fields = prepared["fields"]
                state.pop("prepared_draft", None)
                state.draft_generation += 1
                st.rerun()
            return
        saved = state.get("draft_fields", ("", "", ""))
        if state.get("draft_notice"):
            st.caption(state.draft_notice)
        recipient = st.text_input("Alıcı (tek adres, isteğe bağlı)", value=saved[0], max_chars=254, key=f"draft_to_{generation}")
        subject = st.text_input("Konu", value=saved[1], max_chars=200, key=f"draft_subject_{generation}")
        body = st.text_area("İleti metni", value=saved[2], max_chars=MAX_BODY, key=f"draft_body_{generation}")
        prepare = st.button("Taslağı hazırla", key=f"draft_prepare_{generation}")
        copy = st.button("Son yanıtı taslağa al", key=f"draft_copy_{generation}", disabled=not any(m["role"] == "assistant" for m in state.messages))
        snapshot = (recipient, subject, body)
        if copy:
            answer = next((m["content"] for m in reversed(state.messages) if m["role"] == "assistant"), "")
            if len(answer) > MAX_BODY:
                st.warning("Son yanıt 30.000 karakteri aşıyor; kopyalanmadı. İstediğiniz bölümü kendiniz ekleyin.")
            else:
                state.draft_fields = (recipient, subject, answer)
                state.draft_notice = "Son yanıt ileti metnine alındı. Göndermeden önce düzenleyin."
                state.draft_generation += 1
                st.rerun()
        if prepare:
            try:
                content = build_draft(*snapshot)
                state.draft_fields = snapshot
                state.prepared_draft = {"fields": snapshot, "content": content}
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def voice_tools(st):
    answer = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), "")
    if not answer:
        return
    with st.expander("🔊 Son yanıtı dinle"):
        enabled = st.checkbox("Seslendirme denetimlerini aç", key="speech_enabled", value=False)
        st.caption("Ek model veya ücretli ses API'si kullanılmaz. Destek, ses kalitesi ve Türkçe ses bulunması tarayıcı/cihazına bağlıdır. Yalnızca tarayıcının yerel olarak bildirdiği sesler seçilir.")
        if enabled:
            render_speech(st, answer)
