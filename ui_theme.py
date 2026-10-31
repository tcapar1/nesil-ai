"""Reference-matched responsive theme for the Nesil AI workspace."""
import streamlit as st


def apply_theme():
    st.markdown(
        """
        <style>
        :root{--navy:#071b58;--blue:#2468f5;--blue2:#438cff;--muted:#7184aa;--line:#e2eafa;--panel:#fff}
        html,body,[class*="css"]{font-family:Inter,"Segoe UI",Arial,sans-serif}
        .stApp{background:linear-gradient(130deg,#f8faff 0%,#f2f6ff 54%,#edf3ff 100%);color:var(--navy)}
        [data-testid="stHeader"]{background:rgba(248,250,255,.94);height:2.6rem}
        [data-testid="stMain"] .block-container{max-width:1800px;padding:1rem clamp(1rem,1.8vw,2rem) 2rem}
        [data-testid="stSidebar"]{background:linear-gradient(180deg,#f8faff,#edf3ff);border-right:1px solid #dfe8f8;min-width:270px!important}
        [data-testid="stSidebar"]>div:first-child{padding:1rem .9rem}
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.5rem}
        [data-testid="stSidebar"] h1{font-size:1.35rem!important;font-weight:800;color:#071b58!important}
        [data-testid="stSidebar"] [data-testid="stExpander"]{background:#ffffffa8;border:1px solid #e1eafa;border-radius:12px}
        [data-testid="stSidebar"] .stButton>button{justify-content:flex-start;text-align:left;background:#ffffffb8;border:1px solid #dce7fa}
        h1,h2,h3{color:var(--navy)!important;letter-spacing:-.035em}
        p,label,.stCaption{color:var(--muted)}
        .nd-topbar{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin:.05rem 0 1rem;padding:.15rem 0 .9rem;border-bottom:1px solid #e2eafa}
        .nd-brand{display:flex;align-items:center;gap:.7rem;min-width:250px}
        .nd-logo{width:54px;height:54px;display:grid;place-items:center;border-radius:17px;background:linear-gradient(145deg,#dceaff,#fff);border:1px solid #d5e4ff;font-size:2rem;box-shadow:0 8px 20px #2768ee18}
        .nd-brand strong{display:block;font-size:1.55rem;font-weight:850;color:#081b58;line-height:1.1}
        .nd-brand span{display:block;font-size:.83rem;color:#58709e;margin-top:.25rem}
        .nd-models{display:flex;align-items:center;gap:.5rem;padding:.3rem;background:#fff;border:1px solid #e4ebf8;border-radius:16px;box-shadow:0 6px 20px #1a3d7a08}
        .nd-model{display:flex;align-items:center;gap:.55rem;padding:.55rem .8rem;border-radius:12px;background:#f4f7fd;color:#0c235e}
        .nd-model b{font-size:1.3rem;color:#2568f5}.nd-model strong{display:block;font-size:.82rem}.nd-model small{display:block;font-size:.68rem;color:#7b8eaf}
        .nd-model-primary{background:linear-gradient(120deg,#2468f5,#438cff);color:white}.nd-model-primary b,.nd-model-primary small{color:white}
        .nd-account{display:flex;align-items:center;gap:.65rem;padding:.45rem .7rem;border-radius:15px;background:#fff;border:1px solid #e4ebf8;min-width:150px}
        .nd-avatar{width:40px;height:40px;display:grid;place-items:center;border-radius:50%;background:linear-gradient(140deg,#2468f5,#55a2ff);color:white;font-weight:800}
        .nd-account strong{display:block;font-size:.83rem;color:#10265e}.nd-account small{display:block;color:#7b8eaf;font-size:.68rem}
        .nd-hero{position:relative;overflow:hidden;min-height:190px;display:flex;align-items:center;justify-content:space-between;padding:1.5rem 2rem;border-radius:20px;border:1px solid #d2e4ff;background:linear-gradient(112deg,#e8edff 0%,#cfe5ff 56%,#8dc6ff 100%);box-shadow:0 12px 30px #2356a20c;margin:.2rem 0 1rem}
        .nd-hero-copy{position:relative;z-index:2;max-width:66%}.nd-eyebrow{font-size:.66rem;font-weight:850;letter-spacing:.15em;color:#3472dc}
        .nd-hero h1{font-size:clamp(1.65rem,2.4vw,2.25rem)!important;color:#071b58!important;margin:.45rem 0 .5rem;font-weight:850}
        .nd-hero p{font-size:.98rem;color:#153b87;line-height:1.6;max-width:670px;margin:0}
        .nd-hero-tags{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:.9rem}.nd-hero-tags span{font-size:.72rem;color:#28549d;background:#ffffff91;border:1px solid #ffffffb8;border-radius:99px;padding:.32rem .6rem}
        .nd-robot-scene{position:absolute;right:3%;top:0;width:36%;height:100%;min-width:210px}
        .nd-orbit{position:absolute;width:185px;height:130px;right:12%;top:25px;border:1px solid #ffffffb8;border-radius:50%;transform:rotate(-25deg)}
        .nd-robot{position:absolute;right:20%;bottom:-22px;width:126px;height:145px;border-radius:48px 48px 24px 24px;background:linear-gradient(145deg,#fff,#cde4ff);border:3px solid #9acaff;box-shadow:inset -10px -10px 20px #5ca0f333,0 15px 25px #2768ee30}
        .nd-robot-face{position:absolute;left:17px;top:24px;width:88px;height:70px;border-radius:25px;background:linear-gradient(145deg,#092b70,#0b4b9c);box-shadow:inset 0 0 12px #42a9ff}
        .nd-robot-face i{position:absolute;top:25px;width:12px;height:17px;border-radius:50%;background:#37caff;box-shadow:0 0 10px #42cfff}.nd-robot-face i:first-child{left:22px}.nd-robot-face i:last-child{right:22px}
        .nd-robot-mouth{position:absolute;left:54px;top:105px;width:20px;height:5px;border-radius:9px;background:#2998f5}
        .nd-antenna{position:absolute;left:59px;top:-17px;width:5px;height:18px;background:#388eff;border-radius:4px}
        .nd-float{position:absolute;display:grid;place-items:center;width:42px;height:42px;border-radius:12px;background:#ffffffd9;border:1px solid #fff;color:#2d73e9;font-size:1.2rem;box-shadow:0 8px 18px #1c58a51a}
        .nd-float-doc{right:68%;top:40px}.nd-float-chart{right:48%;top:20px}.nd-float-web{right:8%;bottom:32px}
        .nd-feature{min-height:82px;display:flex;align-items:center;gap:.65rem;padding:.75rem .65rem;border:1px solid #e3ebfa;border-radius:15px;background:#ffffffed;box-shadow:0 6px 18px #1e3d7810}
        .nd-feature-icon{width:40px;height:40px;flex:0 0 40px;display:grid;place-items:center;border-radius:12px;background:#edf4ff;font-size:1.35rem}
        .nd-feature strong{display:block;font-size:.78rem;color:#0c235e;line-height:1.35}.nd-feature small{display:block;font-size:.65rem;color:#7184aa;line-height:1.4;margin-top:.2rem}
        .nd-arrow{margin-left:auto;color:#286cf3;font-size:1.1rem}
        .stButton>button,.stDownloadButton>button{border-radius:11px;min-height:2.35rem;font-weight:650;border:1px solid #dce6f7;background:#fff;color:#1a3979;transition:all .15s ease}
        .stButton>button[kind="primary"]{background:linear-gradient(120deg,#2468f5,#438cff);border-color:#2468f5;color:white;box-shadow:0 7px 16px #2468f52a}
        .stButton>button:hover,.stDownloadButton>button:hover{border-color:#8db2fb;color:#1554d2;transform:translateY(-1px)}
        [data-testid="stChatMessage"]{border:1px solid #e3ebf8;border-radius:16px;padding:1rem;background:#fff;box-shadow:0 5px 16px #173b7710}
        [data-testid="stChatInput"]{border:1px solid #d4e2fa;border-radius:17px;background:#fff;box-shadow:0 8px 24px #1d4d9412}
        [data-testid="stChatInput"]:focus-within{border-color:#77a4fb;box-shadow:0 0 0 3px #2468f51a}
        [data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stSelectbox"] [data-baseweb="select"]>div{border-radius:11px!important;border-color:#dce6f7!important;background:#fff!important}
        [data-testid="stExpander"]{border:1px solid #e4ebf7;border-radius:13px;background:#ffffffdb;overflow:hidden}
        [data-testid="stFileUploader"]{border:1px dashed #a9c3f2;border-radius:14px;padding:.4rem;background:#fbfcff}
        .nd-rail-heading{display:flex;justify-content:space-between;align-items:center;margin:.35rem 0 .8rem}.nd-rail-heading strong{font-size:1.05rem;color:#0b205c}.nd-rail-heading span{font-size:.68rem;color:#2d70ec}
        .nd-rail-item,.nd-chat-item{display:flex;align-items:center;gap:.65rem;padding:.55rem 0;border-bottom:1px solid #edf1f8}
        .nd-file-icon{width:42px;height:42px;display:grid;place-items:center;border-radius:11px;background:#f2f6ff;font-size:1.3rem}
        .nd-rail-item strong,.nd-chat-item strong{display:block;font-size:.76rem;color:#14295d;overflow-wrap:anywhere}.nd-rail-item small,.nd-chat-item small{display:block;font-size:.67rem;color:#8192b1;margin-top:.15rem}
        .nd-chat-item>span{width:34px;height:34px;display:grid;place-items:center;border-radius:50%;background:#f1f5ff;color:#174fbb}
        .nd-model-secure{background:#f4fbf8;border:1px solid #dcefe6}
        .nd-chat-welcome{display:flex;align-items:center;gap:.85rem;padding:1rem 1.1rem;margin:.9rem 0 .65rem;border:1px solid #e2eafa;border-radius:16px;background:#fff}
        .nd-chat-bubble{width:46px;height:46px;flex:0 0 46px;display:grid;place-items:center;border-radius:50%;background:linear-gradient(135deg,#2468f5,#55a0ff);color:#fff;font-size:1.6rem}
        .nd-chat-welcome strong{display:block;color:#10265e;font-size:1.08rem}
        .nd-chat-welcome p{margin:.2rem 0 0;color:#7184aa;font-size:.83rem}
        [data-testid="stMain"] .stButton>button{white-space:normal;line-height:1.35}
        [data-testid="stMain"] [data-testid="stVerticalBlock"]>div:has(>.nd-rail-heading){padding:.3rem 0}
                @media(max-width:1200px){.nd-models{gap:.2rem}.nd-model{padding:.45rem}.nd-model small{display:none}.nd-brand{min-width:180px}}
        @media(max-width:900px){.nd-topbar{flex-wrap:wrap}.nd-models{order:3;width:100%;justify-content:space-between}.nd-hero-copy{max-width:75%}.nd-robot-scene{opacity:.65}}
        @media(max-width:700px){[data-testid="stMain"] .block-container{padding:.6rem .65rem 1.2rem}.nd-brand{min-width:0}.nd-brand strong{font-size:1.25rem}.nd-account{margin-left:auto;min-width:0}.nd-account small{display:none}.nd-models{overflow-x:auto}.nd-model{flex:1;justify-content:center}.nd-model strong{font-size:.7rem}.nd-hero{min-height:205px;padding:1.1rem}.nd-hero-copy{max-width:100%}.nd-hero p{font-size:.86rem}.nd-robot-scene{opacity:.15;right:-8%;width:55%}.nd-feature{min-height:90px;padding:.5rem;gap:.4rem}.nd-feature-icon{width:32px;height:32px;flex-basis:32px;font-size:1rem}.nd-feature strong{font-size:.68rem}.nd-feature small{font-size:.58rem}}
        @media(prefers-reduced-motion:reduce){*,*::before,*::after{transition-duration:.01ms!important;animation-duration:.01ms!important}}
        </style>
        """, unsafe_allow_html=True
    )
