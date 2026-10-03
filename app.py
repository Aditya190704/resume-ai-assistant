"""Streamlit entry point for Resume AI Assistant."""

import html
import logging
import re
import time
from datetime import datetime

import streamlit as st

from config import settings
from services.gemini_service import GeminiServiceError, generate_resume_response
from services.resume_parser import ResumeParserError, extract_resume_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

EXAMPLE_QUESTIONS = [
    "Summarize my resume.",
    "What are my strongest technical skills?",
    "Explain my projects.",
    "What technologies have I worked with?",
    "Generate interview questions based on my resume.",
    "Create a professional summary.",
    "What skills are missing or unclear?",
    "What areas of my resume could be improved?",
]

MAX_HISTORY = 20  # how many past answers to keep in this browser session

# NOTE: no blank lines inside the HTML/CSS blocks (Markdown would break them).
CUSTOM_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root { color-scheme: light; }
html, body, .stApp { font-family: 'Inter', sans-serif; color: #1e293b; }
.stApp { background: radial-gradient(circle at 10% 0%, #e6f4f1 0%, transparent 45%), radial-gradient(circle at 100% 100%, #e8eef9 0%, transparent 45%), #f8fafc; }
@keyframes fadeUp { from {opacity: 0; transform: translateY(16px)} to {opacity: 1; transform: translateY(0)} }
@keyframes drift { 0%, 100% {transform: translate(0, 0)} 50% {transform: translate(24px, -16px)} }
@keyframes floatIcon { 0%, 100% {transform: translateY(0)} 50% {transform: translateY(-9px)} }
@keyframes bounce { 0%, 80%, 100% {transform: scale(.6); opacity: .5} 40% {transform: scale(1); opacity: 1} }
@keyframes shimmer { 0% {background-position: -500px 0} 100% {background-position: 500px 0} }
@keyframes sweep { from {left: -60%} to {left: 140%} }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1240px; }
.hero { position: relative; overflow: hidden; border-radius: 24px; padding: 2.4rem 2.2rem; margin-bottom: 1.6rem; background: linear-gradient(120deg, #0f172a 0%, #134e4a 58%, #0f766e 100%); box-shadow: 0 18px 50px rgba(15,23,42,.22); animation: fadeUp .7s ease both; }
.hero::before { content: ""; position: absolute; width: 320px; height: 320px; right: -80px; top: -120px; border-radius: 50%; background: radial-gradient(circle, rgba(45,212,191,.35), transparent 70%); animation: drift 9s ease-in-out infinite; }
.hero::after { content: ""; position: absolute; width: 260px; height: 260px; left: -70px; bottom: -130px; border-radius: 50%; background: radial-gradient(circle, rgba(148,163,184,.28), transparent 70%); animation: drift 12s ease-in-out infinite reverse; }
.hero h1 { position: relative; z-index: 1; font-size: 2.3rem; font-weight: 800; margin: 0; padding: 0; color: #ffffff !important; letter-spacing: -.5px; }
.hero p { position: relative; z-index: 1; margin: .5rem 0 1.1rem; font-size: 1.05rem; color: #cbd5e1 !important; }
.chip { position: relative; z-index: 1; display: inline-block; margin: 0 .4rem .4rem 0; padding: .35rem .9rem; border-radius: 999px; font-size: .8rem; font-weight: 600; color: #e2e8f0 !important; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.22); }
.st-key-input_card, .st-key-output_card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 22px; padding: 1.6rem; box-shadow: 0 10px 34px rgba(15,23,42,.07); animation: fadeUp .7s ease both; transition: box-shadow .3s ease, transform .3s ease; }
.st-key-output_card { animation-delay: .12s; min-height: 540px; }
.st-key-input_card { animation-delay: .24s; }
.st-key-input_card:hover, .st-key-output_card:hover { box-shadow: 0 18px 46px rgba(15,23,42,.12); transform: translateY(-2px); }
.card-title { display: flex; align-items: center; gap: .55rem; font-size: 1.15rem; font-weight: 700; color: #0f172a; padding-bottom: .8rem; margin-bottom: .6rem; border-bottom: 1px solid #f1f5f9; }
.step-label { display: flex; align-items: center; gap: .6rem; font-weight: 600; font-size: .95rem; color: #0f172a; margin: 1.1rem 0 .55rem; }
.step-label span { width: 24px; height: 24px; border-radius: 50%; background: #0f766e; color: #fff; font-size: .78rem; display: flex; align-items: center; justify-content: center; }
.file-badge { display: inline-flex; align-items: center; gap: .5rem; margin-top: .6rem; padding: .4rem .9rem; border-radius: 999px; background: #f0fdfa; border: 1px solid #99f6e4; color: #0f766e; font-weight: 600; font-size: .85rem; animation: fadeUp .4s ease both; }
[data-testid="stFileUploaderDropzone"] { background: #f8fafc; border: 2px dashed #94a3b8; border-radius: 16px; transition: all .25s ease; }
[data-testid="stFileUploaderDropzone"]:hover { border-color: #0f766e; background: #f0fdfa; transform: translateY(-2px); }
[data-testid="stFileUploader"] small, [data-testid="stFileUploader"] span, [data-testid="stFileUploader"] p { color: #475569 !important; }
[data-testid="stFileUploaderDropzone"] button { background: #ffffff; color: #0f766e !important; border: 1px solid #99f6e4; border-radius: 10px; }
.stButton > button { width: 100%; border-radius: 12px; font-weight: 600; transition: all .25s ease; position: relative; overflow: hidden; }
.stButton > button[data-testid="stBaseButton-secondary"] { background: #ffffff; border: 1px solid #cbd5e1; min-height: 3rem; }
.stButton > button[data-testid="stBaseButton-secondary"] p { color: #0f172a !important; font-size: .85rem; }
.stButton > button[data-testid="stBaseButton-secondary"]:hover { background: #f0fdfa; border-color: #0f766e; transform: translateY(-2px); box-shadow: 0 8px 18px rgba(15,118,110,.15); }
.stButton > button[data-testid="stBaseButton-primary"] { border: none; padding: .8rem 1rem; background: linear-gradient(135deg, #0f766e, #14b8a6); box-shadow: 0 10px 24px rgba(15,118,110,.35); }
.stButton > button[data-testid="stBaseButton-primary"] p { color: #ffffff !important; font-size: 1rem; }
.stButton > button[data-testid="stBaseButton-primary"]:hover { transform: translateY(-2px); box-shadow: 0 14px 30px rgba(15,118,110,.45); }
.stButton > button[data-testid="stBaseButton-primary"]::after { content: ""; position: absolute; top: 0; left: -60%; width: 40%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255,255,255,.35), transparent); transform: skewX(-20deg); }
.stButton > button[data-testid="stBaseButton-primary"]:hover::after { animation: sweep .8s ease; }
.stTextArea [data-baseweb="textarea"] { background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 14px; transition: all .25s ease; }
.stTextArea [data-baseweb="textarea"]:focus-within { border-color: #0f766e; box-shadow: 0 0 0 4px rgba(20,184,166,.18); }
.stTextArea textarea { background: #ffffff !important; color: #0f172a !important; -webkit-text-fill-color: #0f172a; }
.stTextArea textarea::placeholder { color: #94a3b8 !important; -webkit-text-fill-color: #94a3b8; }
.st-key-output_card [data-testid="stMarkdownContainer"] { animation: fadeUp .5s ease both; }
.st-key-output_card [data-testid="stMarkdownContainer"] p, .st-key-output_card [data-testid="stMarkdownContainer"] li, .st-key-output_card [data-testid="stMarkdownContainer"] span { color: #334155; line-height: 1.7; }
.st-key-output_card [data-testid="stMarkdownContainer"] h1, .st-key-output_card [data-testid="stMarkdownContainer"] h2, .st-key-output_card [data-testid="stMarkdownContainer"] h3, .st-key-output_card [data-testid="stMarkdownContainer"] strong { color: #0f172a; }
.st-key-output_card h3 { border-left: 4px solid #14b8a6; padding-left: .7rem; margin-top: 1.2rem; }
.alert { border-radius: 14px; padding: .9rem 1.1rem; font-weight: 500; margin-bottom: .8rem; animation: fadeUp .4s ease both; }
.alert.error { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }
.alert.info { background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; }
.empty-state { text-align: center; padding: 4.5rem 1rem; color: #64748b; }
.empty-state .icon { font-size: 3.6rem; display: inline-block; animation: floatIcon 3s ease-in-out infinite; }
.empty-state h4 { color: #0f172a; margin: 1rem 0 .3rem; font-size: 1.15rem; font-weight: 700; }
.dots { display: flex; gap: .45rem; justify-content: center; margin: 1.5rem 0 1rem; }
.dots span { width: 12px; height: 12px; border-radius: 50%; background: linear-gradient(135deg, #0f766e, #2dd4bf); animation: bounce 1.2s infinite ease-in-out; }
.dots span:nth-child(2) { animation-delay: .15s; }
.dots span:nth-child(3) { animation-delay: .3s; }
.loader-text { text-align: center; color: #0f766e; font-weight: 600; margin-bottom: 1.4rem; }
.skeleton { height: 14px; border-radius: 8px; margin: .8rem 0; background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 37%, #f1f5f9 63%); background-size: 1000px 100%; animation: shimmer 1.4s infinite linear; }
.privacy-note { text-align: center; color: #94a3b8; font-size: .8rem; margin-top: 1.4rem; }
[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e2e8f0; }
[data-testid="stSidebar"] h3 { color: #0f172a; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #64748b; }
.stDownloadButton > button { width: 100%; border-radius: 12px; font-weight: 600; background: #ffffff; border: 1px solid #99f6e4; margin-top: .8rem; transition: all .25s ease; }
.stDownloadButton > button p { color: #0f766e !important; }
.stDownloadButton > button:hover { background: #f0fdfa; border-color: #0f766e; transform: translateY(-2px); }
</style>"""

HERO_HTML = (
    '<div class="hero">'
    "<h1>📄 Resume AI Assistant</h1>"
    "<p>Upload your resume and ask questions about it.</p>"
    '<span class="chip">🔒 Processed in memory, never stored</span>'
    '<span class="chip">⚡ Powered by Gemini on Vertex AI</span>'
    '<span class="chip">📑 PDF · DOCX · TXT</span>'
    "</div>"
)

EMPTY_HTML = (
    '<div class="empty-state">'
    '<div class="icon">✨</div>'
    "<h4>Your answer will appear here</h4>"
    "<div>Upload a resume, ask a question and click Generate Response.</div>"
    "</div>"
)

LOADING_HTML = (
    '<div class="dots"><span></span><span></span><span></span></div>'
    '<div class="loader-text">Reading your resume and thinking...</div>'
    '<div class="skeleton" style="width:90%"></div>'
    '<div class="skeleton" style="width:75%"></div>'
    '<div class="skeleton" style="width:85%"></div>'
    '<div class="skeleton" style="width:60%"></div>'
)


def set_question(question: str) -> None:
    st.session_state["question"] = question


def show_history_item(index: int) -> None:
    """Load an old answer back into the output card."""
    item = st.session_state["history"][index]
    st.session_state.update(
        response=item["response"],
        question=item["question"],
        error=None,
        notice=None,
        animate=False,
    )


def clear_history() -> None:
    st.session_state["history"] = []


def stream_words(text: str):
    """Yield the response piece by piece for a typing effect."""
    for token in re.findall(r"\s+|\S+", text):
        yield token
        if not token.isspace():
            time.sleep(0.01)


def alert_html(kind: str, message: str) -> str:
    return f'<div class="alert {kind}">{html.escape(message)}</div>'


def run_generation(uploaded_file, question: str) -> None:
    """Validate input, extract text, call Gemini, store result in session state."""
    st.session_state.update(response=None, error=None, notice=None, animate=False)

    if uploaded_file is None:
        st.session_state["error"] = "Please upload your resume first."
        return
    if not question.strip():
        st.session_state["error"] = "Please enter a question about your resume."
        return
    if uploaded_file.size > settings.MAX_FILE_SIZE_BYTES:
        st.session_state["error"] = (
            f"File is too large. Please upload a file smaller than "
            f"{settings.MAX_FILE_SIZE_MB} MB."
        )
        return

    try:
        resume_text = extract_resume_text(uploaded_file.name, uploaded_file.getvalue())
        if len(resume_text) > settings.MAX_RESUME_CHARS:
            st.session_state["notice"] = (
                "Your resume is very long, so only the first part was analysed."
            )
        response = generate_resume_response(resume_text, question.strip())
        st.session_state["response"] = response
        st.session_state["animate"] = True
        st.session_state["history"].insert(
            0,
            {
                "question": question.strip(),
                "file": uploaded_file.name,
                "response": response,
                "time": datetime.now().strftime("%H:%M"),
            },
        )
        del st.session_state["history"][MAX_HISTORY:]
    except (ResumeParserError, GeminiServiceError) as exc:
        st.session_state["error"] = str(exc)
    except Exception:
        logger.exception("Unexpected error")
        st.session_state["error"] = "Something went wrong. Please try again."


def render_output(slot) -> None:
    """Draw the error, the response, or the empty state inside the slot."""
    with slot.container():
        if st.session_state["error"]:
            st.markdown(alert_html("error", st.session_state["error"]), unsafe_allow_html=True)
        elif st.session_state["response"]:
            if st.session_state["notice"]:
                st.markdown(alert_html("info", st.session_state["notice"]), unsafe_allow_html=True)
            if st.session_state["animate"]:
                st.write_stream(stream_words(st.session_state["response"]))
                st.session_state["animate"] = False
            else:
                st.markdown(st.session_state["response"])
        else:
            st.markdown(EMPTY_HTML, unsafe_allow_html=True)


def render_sidebar() -> None:
    """Show this session's past questions. Click one to reopen its answer."""
    with st.sidebar:
        st.markdown("### 🕘 History")
        history = st.session_state["history"]
        if not history:
            st.caption("Your questions from this session will appear here.")
            return
        st.caption("Click a question to open its answer.")
        for index, item in enumerate(history):
            question = item["question"]
            short = question if len(question) <= 38 else question[:38] + "…"
            st.button(
                f'{item["time"]} · {short}',
                key=f"history_{index}",
                on_click=show_history_item,
                args=(index,),
            )
        st.button("🗑️ Clear history", key="clear_history", on_click=clear_history)


def main() -> None:
    st.set_page_config(
        page_title="Resume AI Assistant",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.session_state.setdefault("question", "")
    st.session_state.setdefault("response", None)
    st.session_state.setdefault("error", None)
    st.session_state.setdefault("notice", None)
    st.session_state.setdefault("animate", False)
    st.session_state.setdefault("history", [])

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(HERO_HTML, unsafe_allow_html=True)

    left, right = st.columns([1.15, 1], gap="large")

    # ---------- RIGHT: input ----------
    with right:
        with st.container(key="input_card"):
            st.markdown('<div class="card-title">📤 Your Input</div>', unsafe_allow_html=True)

            st.markdown('<div class="step-label"><span>1</span> Upload resume</div>', unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "Upload PDF / DOCX / TXT",
                type=[ext.lstrip(".") for ext in settings.SUPPORTED_EXTENSIONS],
                label_visibility="collapsed",
            )
            if uploaded_file is not None:
                size_kb = uploaded_file.size / 1024
                st.markdown(
                    f'<div class="file-badge">✓ {html.escape(uploaded_file.name)} '
                    f"· {size_kb:.0f} KB</div>",
                    unsafe_allow_html=True,
                )

            st.markdown('<div class="step-label"><span>2</span> Try an example</div>', unsafe_allow_html=True)
            columns = st.columns(2)
            for index, example in enumerate(EXAMPLE_QUESTIONS):
                columns[index % 2].button(
                    example,
                    key=f"example_{index}",
                    on_click=set_question,
                    args=(example,),
                )

            st.markdown('<div class="step-label"><span>3</span> Ask your question</div>', unsafe_allow_html=True)
            question = st.text_area(
                "Ask something about your resume",
                key="question",
                height=110,
                placeholder="e.g. What are my strongest technical skills?",
                label_visibility="collapsed",
            )

            clicked = st.button("✨ Generate Response", type="primary")

    # ---------- LEFT: output ----------
    with left:
        with st.container(key="output_card"):
            st.markdown('<div class="card-title">💡 AI Response</div>', unsafe_allow_html=True)
            slot = st.empty()
            if clicked:
                slot.markdown(LOADING_HTML, unsafe_allow_html=True)
                run_generation(uploaded_file, question)
            render_output(slot)
            if st.session_state["response"]:
                st.download_button(
                    "⬇️ Download answer",
                    data=st.session_state["response"],
                    file_name="resume_answer.md",
                    mime="text/markdown",
                )

    # Sidebar is drawn last so a brand-new answer shows up in History immediately.
    render_sidebar()

    st.markdown(
        '<div class="privacy-note">Your resume is not stored. Session history stays only until you refresh or close this tab.</div>',
        unsafe_allow_html=True,
    )


main()