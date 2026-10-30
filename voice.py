"""Fixed speech controls; untrusted text is passed only as base64 data."""
import base64
from pathlib import Path

MAX_SPEECH = 8000


def speech_html(text):
    encoded = base64.b64encode(text[:MAX_SPEECH].encode("utf-8")).decode("ascii")
    template = Path(__file__).with_name("speech_player.html").read_text(encoding="utf-8")
    return template.replace("__SPEECH_DATA__", encoded)


def render_speech(st, text):
    if len(text) > MAX_SPEECH:
        st.caption("Seslendirme ilk 8.000 karakterle sınırlı.")
    html = speech_html(text)
    if callable(getattr(st, "iframe", None)):
        st.iframe(html, height=220)
    else:
        # Compatibility with the project's minimum Streamlit 1.40.
        from streamlit.components.v1 import html as component_html
        component_html(html, height=220, scrolling=False)
