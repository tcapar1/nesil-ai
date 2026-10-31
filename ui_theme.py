"""Nesil AI premium, responsive Streamlit presentation layer."""
import streamlit as st


def apply_theme():
    st.markdown(
        """
        <style>
        :root {
          --nesil-ink: #17243b;
          --nesil-muted: #66758c;
          --nesil-blue: #315be8;
          --nesil-line: #e6ebf3;
          --nesil-surface: #f6f8fc;
        }
        html, body, [class*="css"] { font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
        .stApp { background: #f7f9fd; color: var(--nesil-ink); }
        [data-testid="stHeader"] { background: rgba(247,249,253,.88); backdrop-filter: blur(12px); }
        [data-testid="stToolbar"] { right: 1rem; }
        [data-testid="stSidebar"] {
          background: linear-gradient(180deg,#ffffff 0%,#f8faff 100%);
          border-right: 1px solid var(--nesil-line);
        }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .72rem; }
        [data-testid="stMain"] .block-container {
          max-width: 1480px; padding: 2.1rem clamp(1rem,3vw,3rem) 3rem;
        }
        h1 { color: #14233d !important; font-weight: 780 !important; letter-spacing: -.045em; }
        h2,h3 { color: #20324e !important; letter-spacing: -.025em; }
        p, label, .stCaption { color: var(--nesil-muted); }
        [data-testid="stChatMessage"] {
          border: 1px solid var(--nesil-line); border-radius: 18px;
          padding: 1rem 1.15rem; margin: .85rem 0;
          box-shadow: 0 5px 18px rgba(26,45,80,.035);
          background: #fff;
        }
        [data-testid="stChatInput"] {
          border: 1px solid #dce4f2; border-radius: 18px;
          box-shadow: 0 10px 30px rgba(30,55,100,.08); background: #fff;
        }
        [data-testid="stChatInput"]:focus-within {
          border-color: #8ba5ff; box-shadow: 0 0 0 3px rgba(49,91,232,.10);
        }
        [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
          border-radius: 11px !important; border-color: #dce4f0 !important;
          background: #fff !important;
        }
        .stButton > button, .stDownloadButton > button {
          border-radius: 11px; min-height: 2.55rem; font-weight: 620;
          border: 1px solid #dce4f0; transition: all .16s ease;
        }
        .stButton > button[kind="primary"] {
          background: linear-gradient(135deg,#315be8,#4777f5);
          border-color: #315be8; color: #fff;
          box-shadow: 0 5px 13px rgba(49,91,232,.16);
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
          border-color: #9bb0f5; transform: translateY(-1px);
        }
        [data-testid="stExpander"] {
          border: 1px solid var(--nesil-line); border-radius: 13px;
          background: rgba(255,255,255,.86); overflow: hidden;
        }
        [data-testid="stFileUploader"] {
          border: 1px dashed #aebde0; border-radius: 14px;
          padding: .45rem; background: #fbfcff;
        }
        [data-testid="stAlert"] { border-radius: 12px; }
        [data-testid="stSidebar"] h1 { font-size: 1.55rem !important; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { line-height: 1.55; }
        [data-testid="stStatusWidget"] { border-radius: 10px; }
        @media (max-width: 900px) {
          [data-testid="stMain"] .block-container { padding: 1rem .85rem 2rem; }
          [data-testid="stChatMessage"] { padding: .8rem; border-radius: 14px; }
          h1 { font-size: 2rem !important; }
        }
        @media (prefers-reduced-motion: reduce) {
          *, *::before, *::after { transition-duration: .01ms !important; animation-duration: .01ms !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
