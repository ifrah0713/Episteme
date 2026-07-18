# ============================================================
# Episteme — Main Web App (app.py)
# ============================================================

import io
import os
import json
import base64
import streamlit as st
from datetime import datetime
from streamlit_oauth import OAuth2Component
from generator import generate_answer, generate_summary
from pdf_loader import process_pdf
from database import (
    create_chat, save_message, load_messages,
    get_all_chats, delete_chat, save_user, get_user,
)
from dotenv import load_dotenv

load_dotenv()

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

MAX_PDFS = 7

st.set_page_config(
    page_title="Episteme", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── Google OAuth ─────────────────────────────────────────────
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

oauth2 = OAuth2Component(
    client_id              = GOOGLE_CLIENT_ID,
    client_secret          = GOOGLE_CLIENT_SECRET,
    authorize_endpoint     = "https://accounts.google.com/o/oauth2/auth",
    token_endpoint         = "https://oauth2.googleapis.com/token",
    refresh_token_endpoint = "https://oauth2.googleapis.com/token",
    revoke_token_endpoint  = "https://oauth2.googleapis.com/revoke",
)

# ─── Session State ────────────────────────────────────────────
for key, val in {
    "messages": [], "uploaded_pdfs": [], "dark_mode": False,
    "chat_id": None, "summary": None,
    "token": None, "user_info": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ─── Login Page ───────────────────────────────────────────────
if not st.session_state.token:
    st.markdown("""
        <style>
        #MainMenu,footer,header{visibility:hidden}
        .stApp{background:#ffffff}
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown(
            "<div style='text-align:center;font-size:3rem;'>⚡</div>"
            "<div style='text-align:center;font-size:2rem;font-weight:700;"
            "margin-bottom:.3rem;'>Episteme</div>"
            "<div style='text-align:center;font-size:1rem;color:#6e6e80;"
            "margin-bottom:2rem;'>Your STEM Knowledge Assistant</div>",
            unsafe_allow_html=True
        )

        result = oauth2.authorize_button(
            name                = "Continue with Google",
            icon                = "https://www.google.com/favicon.ico",
            redirect_uri = os.getenv("REDIRECT_URI", "http://localhost:8501"),
            scope               = "openid email profile",
            key                 = "google_login",
            use_container_width = True,
        )

        if result and "token" in result:
            st.session_state.token = result["token"]
            id_token = result["token"].get("id_token", "")
            if id_token:
                try:
                    payload  = id_token.split(".")[1]
                    payload += "=" * (4 - len(payload) % 4)
                    data     = json.loads(base64.b64decode(payload))
                    st.session_state.user_info = {
                        "name"   : data.get("name", "User"),
                        "email"  : data.get("email", ""),
                        "picture": data.get("picture", ""),
                    }
                except Exception:
                    st.session_state.user_info = {
                        "name": "User", "email": "", "picture": ""
                    }
            st.rerun()
    st.stop()

# ─── User Info ────────────────────────────────────────────────
user_name  = st.session_state.user_info.get("name", "User")
user_email = st.session_state.user_info.get("email", "")
user_pic   = st.session_state.user_info.get("picture", "")

# ─── Theme ────────────────────────────────────────────────────
D = st.session_state.dark_mode
BG_MAIN    = "#212121" if D else "#ffffff"
BG_SIDEBAR = "#171717" if D else "#f9f9f9"
BG_INPUT   = "#2f2f2f" if D else "#f4f4f4"
BG_HOVER   = "#3a3a3a" if D else "#ebebeb"
BG_USER    = "#2f2f2f" if D else "#f0f0f0"
TEXT_MAIN  = "#ececec" if D else "#0d0d0d"
TEXT_SUB   = "#8e8ea0" if D else "#6e6e80"
TEXT_SIDE  = "#c5c5d2" if D else "#353740"
BORDER     = "#383838" if D else "#e5e5e5"
ACCENT     = "#10a37f"
SRC_BG     = "#1a2e28" if D else "#f0fdf4"
SRC_TX     = "#4ade80" if D else "#166534"
THEME_ICO  = "☀️" if D else "🌙"
CH_BG = "#1a2e1a" if D else "#f0fdf4"
CH_BD = "#4ade8044" if D else "#86efac"
CH_TX = "#4ade80"  if D else "#166534"
CM_BG = "#2e2a1a" if D else "#fffbeb"
CM_BD = "#f59e0b44" if D else "#fcd34d"
CM_TX = "#f59e0b"  if D else "#92400e"
CL_BG = "#2e1a1a" if D else "#fef2f2"
CL_BD = "#ef444444" if D else "#fca5a5"
CL_TX = "#ef4444"  if D else "#991b1b"

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
#MainMenu,footer,header{{visibility:hidden}}
*{{font-family:'Inter',sans-serif!important}}
.stApp{{background:{BG_MAIN};color:{TEXT_MAIN}}}
[data-testid="stSidebar"]{{
    background:{BG_SIDEBAR}!important;
    border-right:1px solid {BORDER}!important;
    min-width:260px!important;
    max-width:260px!important;
    transform:translateX(0)!important;
    display:block!important;
    visibility:visible!important;
    opacity:1!important;
}}
section[data-testid="stSidebar"][aria-expanded="false"]{{
    transform:translateX(0)!important;
    min-width:260px!important;
    display:block!important;
}}
[data-testid="stSidebar"] *{{color:{TEXT_SIDE}!important}}
[data-testid="collapsedControl"]{{display:none!important}}
.main .block-container{{max-width:760px;margin:0 auto;padding-top:0!important;padding-bottom:8rem!important}}
.greeting{{font-size:2.4rem;font-weight:600;color:{TEXT_MAIN};text-align:center;margin-top:8rem;margin-bottom:.3rem;letter-spacing:-.5px}}
.greeting span{{color:{ACCENT}}}
.tagline{{font-size:.88rem;color:{TEXT_SUB};text-align:center;margin-bottom:2rem}}
[data-testid="chatAvatarIcon-user"],[data-testid="chatAvatarIcon-assistant"],
[data-testid="stChatMessageAvatarUser"],[data-testid="stChatMessageAvatarAssistant"]{{display:none!important}}
[data-testid="stChatMessage"]{{background:transparent!important;border:none!important;padding:.4rem 0!important;max-width:760px;margin:0 auto!important}}
.user-wrap{{display:flex;justify-content:flex-end;margin-bottom:6px}}
.user-bubble{{background:{BG_USER};border-radius:18px 18px 4px 18px;padding:10px 16px;max-width:85%;font-size:.95rem;color:{TEXT_MAIN};line-height:1.5}}
[data-testid="stBottom"]{{background:{BG_MAIN}!important;border-top:1px solid {BORDER}!important;padding:.5rem 0 0!important}}
.stChatFloatingInputContainer{{background:transparent!important;border:none!important;box-shadow:none!important;max-width:760px!important;margin:0 auto!important;padding:0!important}}
[data-testid="stChatInput"]{{background:{BG_INPUT}!important;border:1px solid {BORDER}!important;border-radius:16px!important;box-shadow:0 2px 6px rgba(0,0,0,.06)!important}}
[data-testid="stChatInput"]:focus-within{{border-color:{ACCENT}!important;box-shadow:0 0 0 2px {ACCENT}22!important}}
[data-testid="stChatInput"]>div{{border:none!important;box-shadow:none!important}}
[data-testid="stChatInput"] textarea{{background:{BG_INPUT}!important;color:{TEXT_MAIN}!important;font-size:.95rem!important;border:none!important;outline:none!important}}
[data-testid="stChatInput"] textarea::placeholder{{color:{TEXT_SUB}!important}}
.stButton>button{{background:transparent!important;color:{TEXT_SIDE}!important;border:none!important;border-radius:8px!important;font-size:.84rem!important;text-align:left!important;padding:6px 10px!important;width:100%!important;transition:background .15s!important;box-shadow:none!important}}
.stButton>button:hover{{background:{BG_HOVER}!important;color:{TEXT_MAIN}!important}}
.stButton>button:focus{{box-shadow:none!important;outline:none!important}}
.src-box{{background:{SRC_BG};border-left:3px solid {ACCENT};padding:5px 10px;border-radius:0 6px 6px 0;font-size:.74rem;margin-top:4px;color:{SRC_TX};word-break:break-all}}
.cite-box{{background:{BG_INPUT};border:1px solid {BORDER};border-radius:8px;padding:10px 14px;font-size:.78rem;color:{TEXT_SUB};line-height:1.8;font-family:monospace!important}}
.fup-label{{font-size:.72rem;font-weight:600;color:{TEXT_SUB};margin:10px 0 5px;text-transform:uppercase;letter-spacing:.05em}}
.conf-h{{display:inline-flex;align-items:center;gap:5px;background:{CH_BG};border:1px solid {CH_BD};border-radius:20px;padding:3px 12px;font-size:.76rem;color:{CH_TX};margin-top:8px;margin-right:4px;font-weight:500}}
.conf-m{{display:inline-flex;align-items:center;gap:5px;background:{CM_BG};border:1px solid {CM_BD};border-radius:20px;padding:3px 12px;font-size:.76rem;color:{CM_TX};margin-top:8px;margin-right:4px;font-weight:500}}
.conf-l{{display:inline-flex;align-items:center;gap:5px;background:{CL_BG};border:1px solid {CL_BD};border-radius:20px;padding:3px 12px;font-size:.76rem;color:{CL_TX};margin-top:8px;margin-right:4px;font-weight:500}}
.badge{{display:inline-block;border:1px solid;border-radius:20px;padding:3px 10px;font-size:.72rem;margin-top:8px;margin-right:4px;font-weight:500}}
.b-ax{{color:#d97706;border-color:#fcd34d;background:#fffbeb}}
.b-pdf{{color:{ACCENT};border-color:#86efac;background:#f0fdf4}}
.b-qz{{color:#7c3aed;border-color:#c4b5fd;background:#f5f3ff}}
.b-e5{{color:#0369a1;border-color:#7dd3fc;background:#f0f9ff}}
.b-cd{{color:#b45309;border-color:#fcd34d;background:#fffbeb}}
.b-dg{{color:#0f766e;border-color:#99f6e4;background:#f0fdfa}}
.b-cp{{color:#be185d;border-color:#f9a8d4;background:#fdf2f8}}
.quiz-box{{background:{BG_INPUT};border:1px solid {BORDER};border-radius:12px;padding:16px;margin-bottom:12px}}
.q-text{{font-size:.95rem;font-weight:500;color:{TEXT_MAIN};margin-bottom:10px}}
.q-ok{{background:{CH_BG};border:1px solid {CH_BD};border-radius:8px;padding:8px 12px;font-size:.88rem;color:{CH_TX};margin-top:4px}}
.q-no{{background:{CL_BG};border:1px solid {CL_BD};border-radius:8px;padding:8px 12px;font-size:.88rem;color:{CL_TX};margin-top:4px}}
.q-ex{{background:{BG_HOVER};border-radius:6px;padding:8px 12px;font-size:.84rem;color:{TEXT_SUB};margin-top:6px}}
.eli-box{{background:linear-gradient(135deg,{BG_INPUT},{BG_HOVER});border:2px solid {ACCENT}44;border-radius:16px;padding:20px;margin-top:4px}}
.eli-lbl{{font-size:.72rem;font-weight:600;color:{ACCENT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px}}
.pdf-ok{{background:{SRC_BG};border-left:3px solid {ACCENT};padding:5px 10px;border-radius:0 6px 6px 0;font-size:.78rem;color:{SRC_TX};margin-top:4px}}
.pdf-er{{background:#fef2f2;border-left:3px solid #ef4444;padding:5px 10px;border-radius:0 6px 6px 0;font-size:.78rem;color:#dc2626;margin-top:4px}}
[data-testid="stTextInput"] input{{background:{BG_INPUT}!important;border:1px solid {BORDER}!important;border-radius:12px!important;color:{TEXT_MAIN}!important;font-size:.95rem!important;padding:12px 16px!important;text-align:center!important}}
[data-testid="stTextInput"] input:focus{{border-color:{ACCENT}!important;box-shadow:0 0 0 2px {ACCENT}22!important;outline:none!important}}
[data-testid="stFileUploader"] label{{display:none!important}}
[data-testid="stFileUploaderDropzone"]{{background:{BG_INPUT}!important;border:1px dashed {BORDER}!important;border-radius:8px!important;padding:8px!important}}
[data-testid="stFileUploaderDropzone"] p,[data-testid="stFileUploaderDropzone"] small,[data-testid="stFileUploaderDropzone"] span{{font-size:.74rem!important;color:{TEXT_SUB}!important}}
[data-testid="stFileUploaderDropzoneInput"]+div{{display:none!important}}
section[data-testid="stFileUploaderDropzone"]>div:nth-child(2){{display:none!important}}
::-webkit-scrollbar{{width:4px}}::-webkit-scrollbar-track{{background:transparent}}::-webkit-scrollbar-thumb{{background:{BORDER};border-radius:10px}}
hr{{border-color:{BORDER}!important;margin:.5rem 0!important}}
.sec-lbl{{font-size:.72rem;font-weight:600;color:{TEXT_SUB};margin-top:12px;margin-bottom:5px;text-transform:uppercase;letter-spacing:.06em}}
@media(max-width:768px){{.greeting{{font-size:1.8rem!important;margin-top:3rem!important}}}}
</style>""", unsafe_allow_html=True)


# ─── Helpers ──────────────────────────────────────────────────
def handle_pdf(files):
    rem = MAX_PDFS - len(st.session_state.uploaded_pdfs)
    for f in files[:rem]:
        if f.name not in st.session_state.uploaded_pdfs:
            with st.spinner(f"Processing {f.name}..."):
                r = process_pdf(f)
            if r["success"]:
                st.session_state.uploaded_pdfs.append(f.name)
                st.markdown(f'<div class="pdf-ok">✅ {f.name} — {r["pages"]} pages</div>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="pdf-er">❌ {r["error"]}</div>',
                            unsafe_allow_html=True)


def make_pdf(text, name):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    story  = []
    story.append(Paragraph("Episteme — Session Summary",
        ParagraphStyle("T", parent=styles["Heading1"], fontSize=22,
                       textColor=colors.HexColor("#10a37f"), spaceAfter=6)))
    story.append(Paragraph(
        f"User: {name} | {datetime.now().strftime('%B %d, %Y %I:%M %p')}",
        ParagraphStyle("M", parent=styles["Normal"], fontSize=10,
                       textColor=colors.gray, spaceAfter=20)))
    story.append(Spacer(1, .2*inch))
    body = ParagraphStyle("B", parent=styles["Normal"],
                          fontSize=11, leading=16, spaceAfter=8)
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, .1*inch))
        elif line.startswith("##"):
            story.append(Paragraph(line.replace("##","").strip(),
                ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14,
                               textColor=colors.HexColor("#10a37f"), spaceAfter=6)))
        elif line.startswith("-"):
            story.append(Paragraph(f"• {line[1:].strip()}", body))
        else:
            story.append(Paragraph(line.replace("**",""), body))
    doc.build(story)
    return buf.getvalue()


def conf_html(c, r):
    if c == "HIGH":
        return '<span class="conf-h">🟢 High Confidence</span>'
    elif c == "MEDIUM":
        return f'<span class="conf-m">🟡 Medium — {r}</span>'
    return '<span class="conf-l">🔴 Low — please verify</span>'


def slabel(icon, text):
    return f'<div class="sec-lbl">{icon} {text}</div>'


def render_quiz(response: dict):
    questions = response.get("questions", [])
    topic     = response.get("topic", "")
    st.markdown('<span class="badge b-qz">🧠 Quiz Mode</span>', unsafe_allow_html=True)
    st.markdown(f"**Quiz: {topic.title()}**")
    if not questions:
        st.warning("Could not generate quiz. Try: 'Quiz me on PID controller'")
        return
    qkey = f"quiz_{st.session_state.chat_id}_{user_email}"
    if qkey not in st.session_state:
        st.session_state[qkey] = {"answers": {}, "submitted": False, "score": 0}
    qs = st.session_state[qkey]
    for i, q in enumerate(questions):
        st.markdown(
            f'<div class="quiz-box"><div class="q-text">Q{i+1}. {q["question"]}</div></div>',
            unsafe_allow_html=True)
        opts = [f"{k}) {v}" for k, v in q["options"].items()]
        if not qs["submitted"]:
            prev_idx = None
            if i in qs["answers"]:
                for j, o in enumerate(opts):
                    if o.startswith(qs["answers"][i]):
                        prev_idx = j
                        break
            sel = st.radio(f"Q{i+1}", opts, index=prev_idx,
                           key=f"{qkey}_r{i}", label_visibility="collapsed")
            if sel:
                qs["answers"][i] = sel[0]
        else:
            user = qs["answers"].get(i, "—")
            corr = q["answer"]
            ok   = user == corr
            st.markdown(
                f'<div class="{"q-ok" if ok else "q-no"}">{"✅" if ok else "❌"} '
                f'Your: {user} | Correct: {corr}</div>',
                unsafe_allow_html=True)
            if q.get("explanation"):
                st.markdown(f'<div class="q-ex">💡 {q["explanation"]}</div>',
                            unsafe_allow_html=True)
    if not qs["submitted"]:
        if st.button("✅ Submit Quiz", key=f"{qkey}_sub"):
            qs["score"]     = sum(1 for i, q in enumerate(questions)
                                  if qs["answers"].get(i,"") == q["answer"])
            qs["submitted"] = True
            st.rerun()
    else:
        s, t  = qs["score"], len(questions)
        emoji = "🏆" if s==t else "👍" if s>=t//2 else "📚"
        st.markdown(
            f"<div style='font-size:1.2rem;font-weight:600;color:{ACCENT};"
            f"margin-top:12px;text-align:center;'>{emoji} Score: {s}/{t}</div>",
            unsafe_allow_html=True)
        if st.button("🔄 Retry", key=f"{qkey}_retry"):
            del st.session_state[qkey]
            st.rerun()


def render_response(response: dict, msg_idx: int = 0):
    mode = response.get("mode", "normal")

    if mode == "quiz":
        render_quiz(response)
        return

    if mode == "compare":
        st.markdown('<span class="badge b-cp">⚖️ Compare Mode</span>', unsafe_allow_html=True)
        cmp  = response.get("compare", {})
        rows = cmp.get("rows", [])
        if cmp.get("title"):
            st.markdown(f"### {cmp['title']}")
        if rows and len(rows) > 1:
            import pandas as pd
            df = pd.DataFrame(rows[1:], columns=rows[0])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("Could not generate comparison.")
        if cmp.get("summary"):
            st.markdown(
                f"<div style='margin-top:12px;padding:12px;background:{BG_INPUT};"
                f"border-radius:8px;font-size:.9rem;color:{TEXT_MAIN};'>"
                f"💡 {cmp['summary']}</div>", unsafe_allow_html=True)
        return

    if mode == "eli5":
        st.markdown('<span class="badge b-e5">🧒 ELI5</span>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="eli-box"><div class="eli-lbl">Simple Explanation</div>'
            f'{response["answer"]}</div>', unsafe_allow_html=True)
        return

    if mode == "code":
        st.markdown('<span class="badge b-cd">💻 Code Analysis</span>', unsafe_allow_html=True)
        st.markdown(response["answer"])
        return

    if mode == "diagram":
        st.markdown('<span class="badge b-dg">📊 Diagram</span>', unsafe_allow_html=True)
        diagram = response.get("diagram", "")
        if diagram:
            try:
                import streamlit.components.v1 as components
                html = f"""
                <div style="background:white;padding:10px;border-radius:8px;">
                <div class="mermaid">{diagram}</div>
                </div>
                <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
                <script>mermaid.initialize({{startOnLoad:true,theme:'neutral'}});</script>
                """
                components.html(html, height=450, scrolling=True)
            except Exception:
                st.code(diagram, language="text")
        else:
            st.warning("Could not generate diagram.")
        return

    # Normal
    answer = response.get("answer", "")
    import re
    blocks = re.findall(r'\$\$(.*?)\$\$', answer, re.DOTALL)
    if blocks:
        parts = re.split(r'\$\$.*?\$\$', answer, flags=re.DOTALL)
        for i, part in enumerate(parts):
            if part.strip():
                st.markdown(part)
            if i < len(blocks):
                st.latex(blocks[i].strip())
    else:
        st.markdown(answer)

    badges = conf_html(response.get("confidence","HIGH"), response.get("reason",""))
    if response.get("is_research"):
        badges += '<span class="badge b-ax">🔬 ArXiv</span>'
    if response.get("pdf_used"):
        badges += '<span class="badge b-pdf">📄 PDF</span>'
    st.markdown(badges, unsafe_allow_html=True)

    sources = response.get("sources", [])
    if sources:
        st.markdown(slabel("📚","Sources"), unsafe_allow_html=True)
        for s in sources[:4]:
            st.markdown(f'<div class="src-box">{s}</div>', unsafe_allow_html=True)

    citations = response.get("citations", "")
    if citations:
        st.markdown(slabel("📝","IEEE Citations"), unsafe_allow_html=True)
        st.markdown(
            f'<div class="cite-box">{citations.replace(chr(10),"<br>")}</div>',
            unsafe_allow_html=True)

    followups = response.get("followups", [])
    if followups:
        st.markdown('<div class="fup-label">💡 You might also ask</div>',
                    unsafe_allow_html=True)
        for i, fq in enumerate(followups):
            if st.button(f"→ {fq}",
                         key=f"fq_{st.session_state.chat_id}_{msg_idx}_{i}",
                         use_container_width=True):
                st.session_state.messages.append({"role":"user","content":fq})
                save_message(st.session_state.chat_id, "user", fq)
                st.rerun()


# ─── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(
            f"<span style='color:{ACCENT};font-size:1rem;font-weight:600;'>"
            f"⚡ Episteme</span>", unsafe_allow_html=True)
    with col2:
        if st.button(THEME_ICO, key="theme"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    # Google user profile
    if user_pic:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;padding:6px 0 10px;'>"
            f"<img src='{user_pic}' style='width:28px;height:28px;border-radius:50%;'>"
            f"<div><div style='font-size:.82rem;color:{TEXT_SIDE};font-weight:500;'>{user_name}</div>"
            f"<div style='font-size:.72rem;color:{TEXT_SUB};'>{user_email}</div></div></div>",
            unsafe_allow_html=True)
    else:
        st.markdown(
            f"<div style='font-size:.78rem;color:{TEXT_SUB};padding:4px 0 8px;'>"
            f"👤 {user_name}</div>", unsafe_allow_html=True)

    st.markdown("---")

    if st.button("✏️  New chat", use_container_width=True, key="new_chat"):
        st.session_state.messages      = []
        st.session_state.uploaded_pdfs = []
        st.session_state.chat_id       = None
        st.session_state.summary       = None
        st.rerun()

    if st.button("🚪  Sign out", use_container_width=True, key="sign_out"):
        st.session_state.token         = None
        st.session_state.user_info     = {}
        st.session_state.messages      = []
        st.session_state.uploaded_pdfs = []
        st.session_state.chat_id       = None
        st.session_state.summary       = None
        st.rerun()

    st.markdown("---")

    # Special Modes
    st.markdown(
        f"<div style='font-size:.72rem;color:{TEXT_SUB};margin-bottom:6px;"
        f"font-weight:600;text-transform:uppercase;'>Special Modes</div>",
        unsafe_allow_html=True)
    for icon, ex in [
        ("🧠","Quiz me on PID"), ("⚖️","Compare Arduino vs RPi"),
        ("🧒","ELI5: Quantum computing"), ("💻","Explain this code: [paste]"),
        ("📊","Draw diagram of PID"),
    ]:
        st.markdown(
            f"<div style='font-size:.74rem;color:{TEXT_SUB};padding:2px 8px;'>"
            f"{icon} <i>{ex}</i></div>", unsafe_allow_html=True)
    st.markdown("---")

    # Session Summary
    if st.session_state.messages:
        if st.button("📋  Session Summary", use_container_width=True):
            with st.spinner("Generating..."):
                st.session_state.summary = generate_summary(st.session_state.messages)
        if st.session_state.summary and REPORTLAB_AVAILABLE:
            st.download_button(
                "⬇️  Download PDF",
                data=make_pdf(st.session_state.summary, user_name),
                file_name=f"episteme_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True)
        st.markdown("---")

    # PDF Upload
    used = len(st.session_state.uploaded_pdfs)
    st.markdown(
        f"<div style='font-size:.76rem;color:{TEXT_SUB};margin-bottom:6px;'>"
        f"📎 Attach PDFs ({used}/{MAX_PDFS})</div>", unsafe_allow_html=True)
    if used < MAX_PDFS:
        pdfs = st.file_uploader("p", type=["pdf"], accept_multiple_files=True,
                                label_visibility="collapsed", key="pdf_up")
        if pdfs:
            handle_pdf(pdfs)
    else:
        st.caption("Maximum PDFs reached")

    for pdf in st.session_state.uploaded_pdfs:
        ca, cb = st.columns([5,1])
        with ca:
            st.markdown(
                f"<div style='font-size:.72rem;color:{TEXT_SUB};padding:2px 0;'>"
                f"📄 {pdf[:18]}{'...' if len(pdf)>18 else ''}</div>",
                unsafe_allow_html=True)
        with cb:
            if st.button("✕", key=f"rm_{pdf}"):
                st.session_state.uploaded_pdfs.remove(pdf)
                st.rerun()

    st.markdown("---")

    # Recent Chats — per user
    st.markdown(
        f"<div style='font-size:.74rem;color:{TEXT_SUB};margin-bottom:6px;'>Recent</div>",
        unsafe_allow_html=True)
    all_chats = get_all_chats(user_email)
    if not all_chats:
        st.markdown(
            f"<div style='font-size:.74rem;color:{TEXT_SUB};'>No chats yet</div>",
            unsafe_allow_html=True)
    else:
        for chat in all_chats[:20]:
            ca, cb = st.columns([5,1])
            with ca:
                lbl = chat["title"][:24] + ("..." if len(chat["title"])>24 else "")
                if st.button(lbl, key=f"c_{chat['id']}", use_container_width=True):
                    st.session_state.chat_id  = chat["id"]
                    st.session_state.messages = load_messages(chat["id"])
                    st.session_state.summary  = None
                    st.rerun()
            with cb:
                if st.button("🗑", key=f"d_{chat['id']}"):
                    delete_chat(chat["id"])
                    if st.session_state.chat_id == chat["id"]:
                        st.session_state.chat_id  = None
                        st.session_state.messages = []
                    st.rerun()

    st.markdown("---")
    st.markdown(
        f"<div style='font-size:.7rem;color:{TEXT_SUB};'>⚡ Knowledge runs deep</div>",
        unsafe_allow_html=True)


# ─── Main ─────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown(
        f'<div class="greeting">How can I help you, <span>{user_name.split()[0]}</span>?</div>',
        unsafe_allow_html=True)
    st.markdown(
        f'<div class="tagline">Science • Technology • Engineering • Mathematics</div>',
        unsafe_allow_html=True)
    st.markdown(
        f"<div style='text-align:center;font-size:.8rem;color:{TEXT_SUB};margin-top:.5rem;'>"
        f"Try: <b>Quiz me on PID</b> · <b>Compare FPGA vs Arduino</b> · "
        f"<b>ELI5: Quantum computing</b> · <b>Draw diagram of PID</b></div>",
        unsafe_allow_html=True)

if st.session_state.summary:
    st.markdown('<div class="sec-lbl">📋 Session Summary</div>', unsafe_allow_html=True)
    st.markdown(st.session_state.summary)
    if REPORTLAB_AVAILABLE:
        st.download_button(
            "⬇️ Download PDF",
            data=make_pdf(st.session_state.summary, user_name),
            file_name=f"episteme_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf")
    st.markdown("---")

# Chat History
for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(
            f'<div class="user-wrap"><div class="user-bubble">{msg["content"]}</div></div>',
            unsafe_allow_html=True)
    else:
        with st.chat_message("assistant"):
            stored = msg.get("response_data")
            if stored:
                render_response(stored, msg_idx=idx)
            else:
                st.markdown(msg["content"])

# Input
prompt = st.chat_input(
    "Ask anything · Quiz me on X · Compare A vs B · ELI5: X · Draw diagram of X")

if prompt:
    if st.session_state.chat_id is None:
        st.session_state.chat_id = create_chat(prompt[:40], user_email)

    save_message(st.session_state.chat_id, "user", prompt)
    st.session_state.messages.append({"role":"user","content":prompt})

    st.markdown(
        f'<div class="user-wrap"><div class="user-bubble">{prompt}</div></div>',
        unsafe_allow_html=True)

    with st.chat_message("assistant"):
        with st.spinner(""):
            response = generate_answer(
                query=prompt,
                chat_history=st.session_state.messages[:-1],
                uploaded_pdfs=st.session_state.uploaded_pdfs,
            )
        render_response(response, msg_idx=len(st.session_state.messages))

    mode = response.get("mode","normal")
    if mode == "normal":
        save_txt = (f"{response.get('answer','')}\n\n"
                    f"**Sources:** {', '.join(response.get('sources',[])[:3])}")
    elif mode == "quiz":
        save_txt = f"[Quiz: {response.get('topic','')}]"
    elif mode == "compare":
        save_txt = f"[Comparison: {response.get('topic','')}]"
    elif mode == "diagram":
        save_txt = f"[Diagram: {response.get('topic','')}]"
    else:
        save_txt = response.get("answer","")

    save_message(st.session_state.chat_id, "assistant", save_txt)
    st.session_state.messages.append({
        "role": "assistant",
        "content": save_txt,
        "response_data": response,
    })