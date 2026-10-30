"""Browser-only Python Mini UI. User code is never executed by Python here."""
import base64
from pathlib import Path
import re

ROOT = Path(__file__).parent
EXAMPLE = '''sayilar = [10, 20, 30]
print("Toplam:", sum(sayilar))
with open("sonuc.csv", "w") as dosya:
    dosya.write("gosterge,deger\\ntoplam," + str(sum(sayilar)) + "\\n")
print("sonuc.csv hazır.")'''


def initial_code(messages):
    latest = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "assistant"), "")
    match = re.search(r"```(?:python|py)[ \t]*\r?\n(.*?)```", latest, re.I | re.S)
    return match.group(1)[:20000] if match else EXAMPLE


def encoded(text):
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def runner_html(code):
    frame = (ROOT / "runner_sandbox.html").read_text(encoding="utf-8")
    frame = frame.replace("__WORKER_B64__", encoded((ROOT / "runner_worker.mjs").read_text(encoding="utf-8")))
    outer = (ROOT / "runner_outer.html").read_text(encoding="utf-8")
    return (outer.replace("__HELPERS__", (ROOT / "runner_limits.mjs").read_text(encoding="utf-8"))
        .replace("__CONFIG_B64__", encoded((ROOT / "runner_runtime.json").read_text(encoding="utf-8")))
        .replace("__FRAME_B64__", encoded(frame)).replace("__CODE_B64__", encoded(code[:20000])))


def runner_tools(st):
    with st.expander("🐍 Python Mini — tarayıcıda çalıştır"):
        st.caption("Deneysel MicroPython: kısa, gözden geçirdiğin Python kodları için. NumPy/Pandas ve tam CPython desteği yoktur. Kod sunucuda çalıştırılmaz; sistem dosyalarına veya uygulamanın API anahtarına erişim verilmez.")
        st.caption("Çalışma motoru ilk kullanımda sürümü ve bütünlüğü sabitlenmiş açık kaynak paketinden indirilir. Kod CDN'ye gönderilmez. Çalışma alanında dış ağ erişimi kapalıdır. Tarayıcı JavaScript belleği/CPU'su için tam bir sert kota yoktur; kötü niyetli kodları çalıştırmayın.")
        if st.checkbox("Python Mini panelini aç", key="python_mini_enabled", value=False):
            html = runner_html(initial_code(st.session_state.messages))
            if callable(getattr(st, "iframe", None)):
                st.iframe(html, height=670)
            else:
                from streamlit.components.v1 import html as component_html
                component_html(html, height=670, scrolling=True)
