"""Premium responsive dashboard theme for Nesil AI."""
import streamlit as st


def apply_theme():
    st.markdown(
        """
        <style>
        :root { --ink:#172746; --muted:#71809a; --blue:#2864ee; --line:#e4ebf7; }
        html,body,[class*="css"] { font-family: Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }
        .stApp { background:linear-gradient(135deg,#f5f8ff 0%,#f8faff 48%,#f1f6ff 100%); color:var(--ink); }
        [data-testid="stHeader"] { background:rgba(247,249,255,.88); backdrop-filter:blur(14px); }
        [data-testid="stSidebar"] { background:linear-gradient(180deg,#fff 0%,#f7faff 100%); border-right:1px solid var(--line); }
        [data-testid="stSidebar"] > div:first-child { padding-top:1rem; }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.62rem; }
        [data-testid="stMain"] .block-container { max-width:1600px; padding:1.2rem clamp(1rem,2.5vw,2.5rem) 2.4rem; }
        h1,h2,h3 { color:var(--ink)!important; letter-spacing:-.035em; }
        h1 { font-weight:800!important; }
        p,label,.stCaption { color:var(--muted); }
        .nesil-topbar { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin:.1rem 0 1rem; padding:.15rem 0 .9rem; border-bottom:1px solid #e6edf8; }
        .nesil-brand { display:flex; align-items:center; gap:.75rem; }
        .nesil-brand-icon { display:grid; place-items:center; width:42px; height:42px; border-radius:14px; color:#fff; font-size:1.5rem; background:linear-gradient(135deg,#2364f4,#53a5ff); box-shadow:0 8px 20px #2864ee35; }
        .nesil-brand strong { display:block; color:#142747; font-size:1.25rem; letter-spacing:-.04em; }
        .nesil-brand small { display:block; color:#7888a2; margin-top:2px; }
        .nesil-status { color:#637692; font-size:.82rem; border:1px solid #e3eaf6; border-radius:99px; padding:.5rem .8rem; background:#ffffffc9; }
        .status-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:#21b67a; margin-right:.35rem; }
        .nesil-hero { position:relative; overflow:hidden; display:flex; justify-content:space-between; align-items:center; min-height:174px; padding:1.5rem 2rem; border-radius:22px; background:linear-gradient(112deg,#e6edff 0%,#dcecff 53%,#b8dcff 100%); border:1px solid #d6e5ff; box-shadow:0 12px 30px #335caa0c; }
        .hero-copy { position:relative; z-index:2; max-width:760px; }
        .hero-kicker { color:#3265d8; font-size:.7rem; font-weight:800; letter-spacing:.14em; }
        .nesil-hero h1 { margin:.45rem 0 .35rem; color:#14284d!important; font-size:clamp(1.7rem,3vw,2.45rem)!important; }
        .nesil-hero p { color:#45618f; font-size:1rem; margin:0; max-width:700px; }
        .hero-pills { display:flex; flex-wrap:wrap; gap:.5rem; margin-top:1rem; }
        .hero-pills span { border:1px solid #ffffffb8; border-radius:99px; padding:.32rem .65rem; color:#36588e; background:#ffffff80; font-size:.75rem; }
        .hero-art { position:relative; width:190px; height:140px; flex:0 0 190px; }
        .art-orbit { position:absolute; border:1px solid #ffffffa8; border-radius:50%; transform:rotate(-25deg); }
        .orbit-one { width:180px;height:90px;top:22px;left:0; }
        .orbit-two { width:145px;height:125px;top:5px;left:20px; }
        .art-core { position:absolute; display:grid;place-items:center; width:86px;height:86px;top:28px;left:54px;border-radius:27px; color:white;font-size:2.5rem;background:linear-gradient(145deg,#2672f5,#54b9ff);box-shadow:0 14px 30px #2864ee55; transform:rotate(-8deg); }
        .art-float { position:absolute;display:grid;place-items:center;width:38px;height:38px;border-radius:12px;background:#ffffffd9;color:#3470e8;box-shadow:0 8px 18px #385c991c;font-size:1.2rem; }
        .float-one { top:8px;left:15px; }.float-two { bottom:5px;right:4px; }
        .nesil-provider-row { display:flex;flex-wrap:wrap;gap:.5rem;margin:.85rem 0 1rem; }
        .provider-chip { border:1px solid #e3eaf6;border-radius:99px;padding:.35rem .7rem;background:#fff;color:#667894;font-size:.76rem; }
        .provider-chip.active { color:#245bd7;background:#eef4ff;border-color:#d5e2ff;font-weight:700; }
        .nesil-quick-card { min-height:104px; padding:.9rem .85rem; display:flex;flex-direction:column;gap:.25rem; background:#fff;border:1px solid #e7edf7;border-radius:16px;box-shadow:0 6px 18px #1e3a6b08; }
        .nesil-quick-card span { color:#2c69ec;font-size:1.2rem; }
        .nesil-quick-card strong { color:#1d3153;font-size:.91rem; }
        .nesil-quick-card small { color:#8190a8;font-size:.74rem; }
        .stButton>button,.stDownloadButton>button { border-radius:11px;min-height:2.5rem;font-weight:620;border:1px solid #dce5f4;transition:all .15s ease; }
        .stButton>button[kind="primary"] { background:linear-gradient(135deg,#2864ee,#4b8cff);border-color:#2864ee;color:white;box-shadow:0 6px 16px #2864ee28; }
        .stButton>button:hover,.stDownloadButton>button:hover { border-color:#9bb7f5;transform:translateY(-1px); }
        [data-testid="stChatMessage"] { border:1px solid #e5ebf5;border-radius:17px;padding:1rem 1.1rem;margin:.7rem 0;background:#fff;box-shadow:0 5px 16px #1d3b6d08; }
        [data-testid="stChatInput"] { border:1px solid #dce6f6;border-radius:17px;background:#fff;box-shadow:0 10px 28px #1d3b6d12; }
        [data-testid="stChatInput"]:focus-within { border-color:#91aff8;box-shadow:0 0 0 3px #2864ee16; }
        [data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stSelectbox"] [data-baseweb="select"]>div { border-radius:11px!important;border-color:#dce5f2!important;background:#fff!important; }
        [data-testid="stExpander"] { border:1px solid #e4ebf5;border-radius:13px;background:#ffffffd9;overflow:hidden; }
        [data-testid="stFileUploader"] { border:1px dashed #adc1e8;border-radius:14px;padding:.4rem;background:#fbfcff; }
        [data-testid="stAlert"] { border-radius:12px; }
        .rail-card { background:#fff;border:1px solid #e6edf7;border-radius:16px;padding:1rem;margin-bottom:.85rem;box-shadow:0 6px 18px #1d3b6d08; }
        .rail-title { display:flex;justify-content:space-between;align-items:center;color:#1b3154;font-weight:750;margin-bottom:.65rem; }
        .rail-item { padding:.55rem 0;border-bottom:1px solid #f0f3f9;color:#344a6d;font-size:.82rem;overflow-wrap:anywhere; }
        .rail-item:last-child { border-bottom:0; }
        .rail-meta { display:block;color:#91a0b7;font-size:.7rem;margin-top:.15rem; }
        [data-testid="stSidebar"] h1 { font-size:1.45rem!important; }
        @media(max-width:1050px) { .hero-art { opacity:.45;position:absolute;right:0; } .nesil-hero { padding:1.25rem; } }
        @media(max-width:760px) { [data-testid="stMain"] .block-container{padding:.8rem .75rem 1.5rem;} .nesil-status{display:none;} .nesil-hero{min-height:160px;} .hero-art{display:none;} .nesil-quick-card{min-height:94px;padding:.65rem;} .nesil-quick-card strong{font-size:.8rem;} }
        @media(prefers-reduced-motion:reduce){*,*::before,*::after{transition-duration:.01ms!important;animation-duration:.01ms!important;}}
        </style>
        """, unsafe_allow_html=True
    )
