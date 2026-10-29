import os, json, urllib.request, urllib.error
import streamlit as st

st.set_page_config(page_title="Nesil AI", page_icon="🤖", layout="centered")
SYSTEM_PROMPT = """Sen Nesil AI adlı Türkçe konuşan genel amaçlı bir yapay zekâ yardımcısısın.
Kullanıcının görevini anlamasına, planlamasına, yazı yazmasına, kod taslağı hazırlamasına ve verileri yorumlamasına yardım et.
Gerçekte yapmadığın işlemleri yaptığını söyleme. Bu ilk sürümde dosya değiştiremez, internette gezemez veya komut çalıştıramazsın.
Riskli işlemlerde insan onayı gerektiğini belirt. Bilmediğin şeyleri uydurma. Yanıtları Türkçe ver."""

def demo_answer(prompt, mode):
    return ("### Demo modu\nNesil AI arayüzü çalışıyor ancak henüz bir yapay zekâ sağlayıcısına bağlanmadı. "
    "Gerçek model yanıtları için Streamlit Secrets bölümüne GROQ_API_KEY eklemelisin.\n\n"
    f"**Çalışma biçimi:** {mode}\n\n**Görevin:**\n{prompt}\n\n"
    "**Başlangıç planı**\n1. Hedefi netleştir.\n2. Gerekli bilgi ve dosyaları belirle.\n"
    "3. Çözümü kontrol edilebilir adımlara böl.\n4. Sonucu doğrula ve riskli işlemlerde onay al.\n\n"
    "Bu yanıt demo şablonudur; gerçek bir model tarafından üretilmemiştir.")

def ask_model(prompt, mode, history):
    try: api_key = st.secrets.get("GROQ_API_KEY")
    except Exception: api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: return demo_answer(prompt, mode)
    messages = [{"role":"system","content":SYSTEM_PROMPT + "\nÇalışma biçimi: " + mode}]
    for item in history[-10:]:
        if item.get("role") in ("user", "assistant"): messages.append({"role":item["role"],"content":item["content"]})
    messages.append({"role":"user","content":prompt})
    payload = {"model":"llama-3.3-70b-versatile","messages":messages,"temperature":0.3,"max_tokens":1800}
    req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=json.dumps(payload).encode("utf-8"), headers={"Authorization":"Bearer " + api_key,"Content-Type":"application/json","User-Agent":"NesilAI/1.0"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as response: data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        if exc.code in (401,403): return f"Groq kimlik doğrulama hatası (HTTP {exc.code}). Groq yanıtı: {details[:400]}\n\nSecrets içindeki GROQ_API_KEY değerini ve GroqCloud anahtarının etkin olduğunu kontrol et."
        if exc.code == 429: return "Kullanım sınırına ulaşıldı. Bir süre sonra tekrar dene."
        return f"Model sağlayıcısı hata döndürdü (HTTP {exc.code}): {details[:400]}"
    except Exception as exc: return f"Model bağlantısı başarısız oldu ({type(exc).__name__}). Biraz sonra tekrar dene."

with st.sidebar:
    st.title("Nesil AI")
    st.caption("Genel amaçlı iş yardımcısı · İlk web sürümü")
    mode = st.selectbox("Çalışma biçimi", ["Genel yardımcı","Görev planlama","Kodlama yardımcısı","Belge ve rapor yardımcısı"])
    st.divider()
    st.markdown("**Özellikler**")
    st.write("• Türkçe sohbet\n• Görev planlama\n• Kod ve rapor taslakları")
    st.divider()
    if st.button("Sohbeti temizle", use_container_width=True): st.session_state.messages = []; st.rerun()
    st.caption("İlk sürüm dosya değiştirmez ve bilgisayar komutları çalıştırmaz.")
st.title("🤖 Nesil AI")
st.write("Görevini yaz; planlama, yazma, kodlama ve analiz konularında yardım al.")
if not st.session_state.get("messages"):
    st.markdown("**Örnek görevler**")
    st.markdown("- Bir web sitesi projesi için yol haritası hazırla.\n- Bir iş sürecini adım adım planla.\n- Python ile CSV raporu oluşturacak kod taslağı yaz.")
for message in st.session_state.get("messages", []):
    with st.chat_message(message["role"]): st.markdown(message["content"])
prompt = st.chat_input("Görevini buraya yaz…")
if prompt:
    prior = st.session_state.get("messages", []).copy()
    st.session_state.setdefault("messages", []).append({"role":"user","content":prompt})
    with st.chat_message("user"): st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Görev değerlendiriliyor…"): answer = ask_model(prompt, mode, prior)
        st.markdown(answer)
    st.session_state["messages"].append({"role":"assistant","content":answer})
st.caption("Nesil AI · Test sürümü. Hassas bilgi girmeyin. Herkese açık yayın öncesi güvenlik ve gizlilik kontrolleri yapılmalıdır.")