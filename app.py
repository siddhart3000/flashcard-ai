"""
Flashcard AI — Ultimate Edition
Groq + Llama 3.3-70B · Spaced Repetition · MCQ · Exam Mode · Analytics · PDF Reports

FIX APPLIED: reportlab is now optional.
If not installed, PDF falls back to a stdlib-only generator.
Install reportlab for the full styled PDF:
    pip install reportlab
"""

import csv
import io
import json
import os
import random
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import streamlit as st
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
load_dotenv()

st.set_page_config(
    page_title="Flashcard AI",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get help": None, "Report a bug": None, "About": None},
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MAX_INPUT_CHARS = 4_000
_MAX_PDF_CHARS   = 12_000
_API_TIMEOUT_S   = 45
_RETRY_ATTEMPTS  = 3
_RETRY_DELAY_S   = 1.5
_MODEL           = "llama-3.3-70b-versatile"

# ---------------------------------------------------------------------------
# Detect reportlab once at startup (no crash if missing)
# ---------------------------------------------------------------------------
try:
    from reportlab.lib.pagesizes import A4 as _RL_A4  # noqa: F401
    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False

SYSTEM_PROMPT = """You are an expert teacher and curriculum designer.

Convert the given text into high-quality flashcards that cover:
- Core concepts and definitions
- Key relationships and patterns
- Edge cases and exceptions
- Worked examples where appropriate

Each card should feel like it was written by a great teacher, not scraped by a bot.
Keep answers concise and optimized for active recall.

Return ONLY valid JSON with no markdown, preamble, or extra text:
{
  "flashcards": [
    {
      "question": "Clear conceptual question",
      "answer": "Concise, memorable explanation",
      "difficulty": "easy | medium | hard",
      "topic": "one short topic label (e.g. Definitions, Concepts, Examples)"
    }
  ]
}"""

EXPLAIN_PROMPT = """You are an expert teacher. A student doesn't fully understand a concept.
Give a richer, clearer explanation with an analogy, a concrete example, and a common misconception to avoid.
Keep it under 120 words. Return plain text only — no bullet points, no markdown."""

MCQ_PROMPT = """You are an exam question writer. Given a flashcard question and answer,
generate 3 plausible but WRONG distractor options. Distractors must be:
- Same type/format as the correct answer
- Clearly wrong to an expert but tempting to a learner
- Concise (max 12 words each)

Return ONLY valid JSON with no markdown:
{"distractors": ["wrong option 1", "wrong option 2", "wrong option 3"]}"""


# ===========================================================================
# STYLES
# ===========================================================================
def inject_styles() -> None:
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
        .stApp {
            background: #080c14;
            background-image:
                radial-gradient(ellipse 80% 50% at 50% -20%, rgba(56,189,248,0.08) 0%, transparent 60%),
                radial-gradient(ellipse 60% 40% at 80% 80%, rgba(139,92,246,0.06) 0%, transparent 50%);
            color: #e2e8f0;
        }
        [data-testid="stSidebar"] {
            background: rgba(10,15,28,0.95) !important;
            border-right: 1px solid rgba(56,189,248,0.12) !important;
            backdrop-filter: blur(20px);
        }
        [data-testid="stSidebar"] > div { padding-top: 1.5rem; }
        .app-title {
            font-size: 2.2rem; font-weight: 700; letter-spacing: -0.03em;
            background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text; margin-bottom: 0.2rem;
        }
        .app-subtitle { color: #64748b; font-size: 0.95rem; margin-bottom: 1.5rem; }
        .section-heading {
            font-size: 1.1rem; font-weight: 600; color: #e2e8f0;
            margin-bottom: 1rem; padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(56,189,248,0.15);
        }
        .glass-card {
            background: rgba(15,23,42,0.7);
            border: 1px solid rgba(56,189,248,0.15);
            border-radius: 20px; padding: 1.8rem 2rem;
            backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
            box-shadow: 0 4px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
            transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
            animation: fadeSlideIn 0.4s ease forwards;
        }
        .glass-card:hover {
            border-color: rgba(56,189,248,0.35);
            box-shadow: 0 8px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(56,189,248,0.1), inset 0 1px 0 rgba(255,255,255,0.07);
            transform: translateY(-3px);
        }
        .answer-card {
            background: rgba(16,24,48,0.75);
            border: 1px solid rgba(129,140,248,0.2);
            border-radius: 20px; padding: 1.8rem 2rem;
            backdrop-filter: blur(16px);
            box-shadow: 0 4px 32px rgba(0,0,0,0.35), 0 0 20px rgba(129,140,248,0.05);
            margin-top: 1rem; animation: fadeSlideIn 0.3s ease forwards;
        }
        .empty-card {
            background: rgba(15,23,42,0.5);
            border: 1px dashed rgba(56,189,248,0.2);
            border-radius: 20px; padding: 3rem 2rem;
            text-align: center; color: #475569;
        }
        .result-card {
            background: rgba(15,23,42,0.8);
            border: 1px solid rgba(56,189,248,0.2);
            border-radius: 20px; padding: 2rem 2.4rem;
            backdrop-filter: blur(16px);
            box-shadow: 0 8px 40px rgba(0,0,0,0.5);
            animation: fadeSlideIn 0.5s ease forwards;
        }
        .mcq-option {
            background: rgba(15,23,42,0.7);
            border: 1px solid rgba(56,189,248,0.15);
            border-radius: 14px; padding: 1rem 1.4rem;
            margin-bottom: 0.6rem; cursor: pointer;
            transition: all 0.2s ease; font-size: 0.98rem; color: #e2e8f0;
        }
        .mcq-option:hover { border-color: #38bdf8; background: rgba(56,189,248,0.06); }
        .mcq-correct { border-color: #22c55e !important; background: rgba(34,197,94,0.08) !important; color: #22c55e !important; }
        .mcq-wrong   { border-color: #ef4444 !important; background: rgba(239,68,68,0.08) !important; color: #ef4444 !important; }
        .exam-timer {
            font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700;
            color: #38bdf8; background: rgba(15,23,42,0.8);
            border: 1px solid rgba(56,189,248,0.2); border-radius: 12px;
            padding: 0.5rem 1.2rem; display: inline-block;
        }
        .exam-timer.warning { color: #fbbf24; border-color: rgba(251,191,36,0.4); }
        .exam-timer.danger  { color: #ef4444; border-color: rgba(239,68,68,0.4); animation: timerPulse 1s infinite; }
        .card-label {
            font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.1em; color: #38bdf8; margin-bottom: 0.75rem;
        }
        .answer-label {
            font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.1em; color: #818cf8; margin-bottom: 0.75rem;
        }
        .card-text { font-size: 1.12rem; line-height: 1.7; color: #e2e8f0; font-weight: 400; }
        .card-counter {
            font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
            color: #475569; margin-bottom: 1rem;
        }
        .badge {
            display: inline-block; padding: 0.25rem 0.7rem; border-radius: 999px;
            font-size: 0.72rem; font-weight: 600; letter-spacing: 0.05em;
            text-transform: uppercase; margin-top: 1.2rem;
        }
        .badge-easy   { background: rgba(34,197,94,0.12);  color: #22c55e;  border: 1px solid rgba(34,197,94,0.25);  }
        .badge-medium { background: rgba(251,191,36,0.12); color: #fbbf24;  border: 1px solid rgba(251,191,36,0.25); }
        .badge-hard   { background: rgba(239,68,68,0.12);  color: #ef4444;  border: 1px solid rgba(239,68,68,0.25);  }
        .topic-tag {
            display: inline-block; padding: 0.18rem 0.55rem; border-radius: 999px;
            font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;
            background: rgba(99,102,241,0.12); color: #818cf8; border: 1px solid rgba(99,102,241,0.2);
            margin-left: 0.4rem;
        }
        .mode-tag {
            display: inline-block; padding: 0.2rem 0.65rem; border-radius: 999px;
            font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em;
            background: rgba(56,189,248,0.1); color: #38bdf8; border: 1px solid rgba(56,189,248,0.2);
            margin-left: 0.4rem;
        }
        .streak-badge {
            display: inline-flex; align-items: center; gap: 0.3rem;
            padding: 0.3rem 0.8rem; border-radius: 999px;
            background: rgba(251,191,36,0.1); color: #fbbf24;
            border: 1px solid rgba(251,191,36,0.25); font-size: 0.82rem; font-weight: 600;
        }
        .metric-box {
            background: rgba(15,23,42,0.7); border: 1px solid rgba(56,189,248,0.12);
            border-radius: 14px; padding: 1rem 1.1rem; text-align: center; backdrop-filter: blur(10px);
        }
        .metric-label { color: #64748b; font-size: 0.75rem; margin-bottom: 0.3rem; font-weight: 500; }
        .metric-value { color: #e2e8f0; font-size: 1.4rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
        .metric-value.green  { color: #22c55e; }
        .metric-value.yellow { color: #fbbf24; }
        .metric-value.red    { color: #ef4444; }
        .metric-value.blue   { color: #38bdf8; }
        .stButton > button {
            border-radius: 12px !important; border: 1px solid rgba(56,189,248,0.2) !important;
            background: rgba(15,23,42,0.8) !important; color: #94a3b8 !important;
            font-family: 'Space Grotesk', sans-serif !important; font-weight: 500 !important;
            transition: all 0.2s ease !important; padding: 0.5rem 1rem !important;
        }
        .stButton > button:hover {
            border-color: #38bdf8 !important; color: #38bdf8 !important;
            background: rgba(56,189,248,0.06) !important;
            box-shadow: 0 0 16px rgba(56,189,248,0.12) !important;
            transform: translateY(-1px) !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #0ea5e9, #6366f1) !important;
            border: none !important; color: #fff !important;
            box-shadow: 0 4px 20px rgba(14,165,233,0.25) !important;
        }
        .stButton > button[kind="primary"]:hover {
            opacity: 0.9 !important; color: #fff !important;
            box-shadow: 0 6px 28px rgba(14,165,233,0.35) !important;
            transform: translateY(-1px) !important;
        }
        .stTextArea textarea, .stTextInput input {
            background: rgba(15,23,42,0.8) !important;
            border: 1px solid rgba(56,189,248,0.15) !important;
            border-radius: 12px !important; color: #e2e8f0 !important;
            font-family: 'Space Grotesk', sans-serif !important;
        }
        .stTextArea textarea:focus, .stTextInput input:focus {
            border-color: #38bdf8 !important; box-shadow: 0 0 0 2px rgba(56,189,248,0.1) !important;
        }
        [data-testid="stFileUploader"] {
            background: rgba(15,23,42,0.6) !important;
            border: 1px dashed rgba(56,189,248,0.25) !important;
            border-radius: 14px !important;
        }
        .stSelectbox > div > div { background: rgba(15,23,42,0.9) !important; border-radius: 10px !important; }
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(15,23,42,0.5) !important; border-radius: 12px !important;
            border: 1px solid rgba(56,189,248,0.1) !important; gap: 0 !important; padding: 4px !important;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px !important; color: #64748b !important;
            font-weight: 500 !important; font-family: 'Space Grotesk', sans-serif !important;
        }
        .stTabs [aria-selected="true"] { background: rgba(56,189,248,0.1) !important; color: #38bdf8 !important; }
        .stProgress > div > div > div {
            background: linear-gradient(90deg, #38bdf8, #818cf8) !important; border-radius: 999px !important;
        }
        .stProgress > div > div { background: rgba(30,41,59,0.6) !important; border-radius: 999px !important; }
        .status-pill {
            display: inline-flex; align-items: center; gap: 0.4rem;
            padding: 0.3rem 0.8rem; border-radius: 999px; font-size: 0.78rem; font-weight: 500;
        }
        .status-ok  { background: rgba(34,197,94,0.1);  color: #22c55e; border: 1px solid rgba(34,197,94,0.2);  }
        .status-err { background: rgba(239,68,68,0.1);  color: #ef4444; border: 1px solid rgba(239,68,68,0.2);  }
        .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
        .dot-pulse { animation: pulse 2s infinite; }
        .explain-box {
            background: rgba(99,102,241,0.07); border: 1px solid rgba(99,102,241,0.2);
            border-radius: 14px; padding: 1.2rem 1.4rem; margin-top: 0.8rem;
            animation: fadeSlideIn 0.3s ease forwards;
        }
        .explain-label { color: #818cf8; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem; }
        .explain-text  { color: #c7d2fe; font-size: 0.95rem; line-height: 1.6; }
        .warn-box {
            background: rgba(251,191,36,0.07); border: 1px solid rgba(251,191,36,0.2);
            border-radius: 12px; padding: 0.75rem 1rem; margin-bottom: 0.6rem;
            font-size: 0.88rem; color: #fbbf24;
        }
        .weak-topic-row {
            display: flex; justify-content: space-between; align-items: center;
            padding: 0.6rem 0.9rem; border-radius: 10px;
            background: rgba(239,68,68,0.06); border: 1px solid rgba(239,68,68,0.15);
            margin-bottom: 0.4rem; font-size: 0.9rem;
        }
        .analytics-row {
            display: flex; justify-content: space-between; align-items: center;
            padding: 0.55rem 0.9rem; border-radius: 10px;
            background: rgba(15,23,42,0.5); border: 1px solid rgba(56,189,248,0.08);
            margin-bottom: 0.35rem; font-size: 0.88rem; color: #94a3b8;
        }
        @keyframes fadeSlideIn { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes timerPulse { 0%,100%{opacity:1} 50%{opacity:0.6} }
        div[data-testid="stVerticalBlock"] { gap: 0.6rem; }
        .stMarkdown p { margin-bottom: 0.4rem; }
        hr { border-color: rgba(56,189,248,0.1) !important; }
        .stInfo    { background: rgba(56,189,248,0.07) !important; border: 1px solid rgba(56,189,248,0.15) !important; border-radius: 12px !important; color: #94a3b8 !important; }
        .stSuccess { background: rgba(34,197,94,0.07)  !important; border: 1px solid rgba(34,197,94,0.2)   !important; border-radius: 12px !important; }
        .stError   { background: rgba(239,68,68,0.07)  !important; border: 1px solid rgba(239,68,68,0.2)   !important; border-radius: 12px !important; }
        .stWarning { background: rgba(251,191,36,0.07) !important; border: 1px solid rgba(251,191,36,0.2)  !important; border-radius: 12px !important; }
        footer { display: none !important; }
        #MainMenu { display: none !important; }
    </style>
    """, unsafe_allow_html=True)


# ===========================================================================
# SESSION STATE
# ===========================================================================
_STATE_DEFAULTS: Dict = {
    "cards": [], "responses": {}, "review_order": [], "current_pointer": 0,
    "show_answer": False, "study_mode": "Normal", "shuffle": False,
    "explain_text": "", "last_input_text": "", "last_num_cards": 10,
    "last_error": "", "generation_pending": False, "topic_filter": "All",
    "current_streak": 0, "best_streak": 0,
    "mcq_options": {}, "mcq_selected": {},
    "exam_active": False, "exam_start_time": None, "exam_duration_s": 300,
    "exam_responses": {}, "exam_order": [], "exam_pointer": 0, "exam_finished": False,
    "show_result_summary": False, "active_tab": 0, "user_name": "", "user_email": "",
}


def init_state() -> None:
    for key, val in _STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val


def reset_learning_state(cards: List[Dict]) -> None:
    st.session_state.cards = cards
    st.session_state.responses = {}
    st.session_state.current_pointer = 0
    st.session_state.show_answer = False
    st.session_state.explain_text = ""
    st.session_state.last_error = ""
    st.session_state.current_streak = 0
    st.session_state.mcq_options = {}
    st.session_state.mcq_selected = {}
    st.session_state.exam_active = False
    st.session_state.exam_finished = False
    st.session_state.exam_responses = {}
    st.session_state.show_result_summary = False
    st.session_state.topic_filter = "All"
    _rebuild_review_order()


# ===========================================================================
# REVIEW ORDER
# ===========================================================================
def _filtered_indices() -> List[int]:
    filt = st.session_state.topic_filter
    if filt == "All":
        return list(range(len(st.session_state.cards)))
    return [i for i, c in enumerate(st.session_state.cards) if c.get("topic", "General") == filt]


def _rebuild_review_order() -> None:
    mode = st.session_state.study_mode
    base_idx = _filtered_indices()
    if not base_idx:
        st.session_state.review_order = []
        return
    known   = [i for i in base_idx if st.session_state.responses.get(i) is True]
    unknown = [i for i in base_idx if st.session_state.responses.get(i) is False]
    unseen  = [i for i in base_idx if i not in st.session_state.responses]
    if mode == "Normal":           order = base_idx[:]
    elif mode == "Unknown First":  order = unknown + unseen + known or base_idx[:]
    elif mode == "Hard Only":      order = [i for i in base_idx if st.session_state.cards[i].get("difficulty") == "hard"] or base_idx[:]
    elif mode == "Review Mistakes":order = unknown or base_idx[:]
    else:                          order = base_idx[:]
    if st.session_state.shuffle:
        random.shuffle(order)
    st.session_state.review_order = order
    st.session_state.current_pointer = min(st.session_state.current_pointer, max(0, len(order) - 1))


# ===========================================================================
# PDF EXTRACTION
# ===========================================================================
@st.cache_data(show_spinner=False)
def _cached_extract_pdf(file_bytes: bytes) -> Tuple[str, str]:
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception:
        text = ""
    if not text.strip():
        try:
            import fitz
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
        except Exception:
            text = ""
    if not text.strip():
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            text = "\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception:
            text = ""
    warning = ""
    if len(text) > _MAX_PDF_CHARS:
        text = text[:_MAX_PDF_CHARS]
        warning = f"PDF was very large — only the first ~{_MAX_PDF_CHARS:,} characters were used."
    return text.strip(), warning


def extract_pdf_text(uploaded_file) -> Tuple[str, str]:
    return _cached_extract_pdf(uploaded_file.read())


# ===========================================================================
# INPUT TRUNCATION
# ===========================================================================
def _truncate_input(text: str) -> Tuple[str, str]:
    if len(text) <= _MAX_INPUT_CHARS:
        return text, ""
    truncated = text[:_MAX_INPUT_CHARS]
    last_period = max(truncated.rfind(". "), truncated.rfind(".\n"))
    if last_period > int(_MAX_INPUT_CHARS * 0.8):
        truncated = truncated[:last_period + 1]
    warn = f"Input was {len(text):,} chars — trimmed to ~{len(truncated):,} for reliable generation."
    return truncated, warn


# ===========================================================================
# API HELPERS
# ===========================================================================
def _get_api_key() -> Optional[str]:
    key = os.getenv("GROQ_API_KEY", "").strip()
    return key if key and key != "your_api_key_here" else None


def _safe_parse_json(raw: str) -> Dict:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```[a-z]*\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found. Snippet: {raw[:200]}")
    return json.loads(cleaned[start:end + 1])


def _sanitise_cards(raw_list: list) -> List[Dict]:
    clean = []
    for c in raw_list:
        if not isinstance(c, dict):
            continue
        q = str(c.get("question", "")).strip()
        a = str(c.get("answer", "")).strip()
        diff = c.get("difficulty", "medium")
        topic = str(c.get("topic", "General")).strip()
        if not q or not a:
            continue
        if diff not in ("easy", "medium", "hard"):
            diff = "medium"
        clean.append({"question": q, "answer": a, "difficulty": diff, "topic": topic})
    return clean


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_generate(text: str, num_cards: int) -> List[Dict]:
    from groq import Groq
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")
    client = Groq(api_key=api_key)
    user_prompt = (
        f"Generate exactly {num_cards} flashcards from the following text. "
        "Vary difficulty across easy, medium, and hard. Assign a short topic label to each card. "
        "Cover all key concepts comprehensively.\n\n" + text
    )
    last_error: Exception = RuntimeError("Unknown error")
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            resp = client.chat.completions.create(
                model=_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
                temperature=0.35, max_tokens=3_000, timeout=_API_TIMEOUT_S,
            )
            raw = resp.choices[0].message.content
            data = _safe_parse_json(raw)
            cards = _sanitise_cards(data.get("flashcards", []))
            if not cards:
                raise ValueError("All returned cards failed validation.")
            return cards
        except json.JSONDecodeError as e:
            last_error = ValueError(f"Malformed JSON (attempt {attempt}): {e}")
        except Exception as e:
            last_error = e
        if attempt < _RETRY_ATTEMPTS:
            time.sleep(_RETRY_DELAY_S * attempt)
    raise RuntimeError(f"Generation failed after {_RETRY_ATTEMPTS} attempts. Last error: {type(last_error).__name__}: {last_error}")


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_explain(question: str, answer: str) -> str:
    from groq import Groq
    api_key = _get_api_key()
    if not api_key:
        return "API key not configured."
    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "system", "content": EXPLAIN_PROMPT}, {"role": "user", "content": f"Question: {question}\nAnswer: {answer}"}],
            temperature=0.5, max_tokens=350, timeout=_API_TIMEOUT_S,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate explanation: {type(e).__name__}: {e}"


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_mcq_distractors(question: str, answer: str) -> List[str]:
    from groq import Groq
    api_key = _get_api_key()
    if not api_key:
        return ["Option A", "Option B", "Option C"]
    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "system", "content": MCQ_PROMPT}, {"role": "user", "content": f"Question: {question}\nCorrect Answer: {answer}"}],
            temperature=0.7, max_tokens=200, timeout=_API_TIMEOUT_S,
        )
        data = _safe_parse_json(resp.choices[0].message.content)
        distractors = data.get("distractors", [])
        if len(distractors) >= 3:
            return [str(d).strip() for d in distractors[:3]]
    except Exception:
        pass
    return ["Option A", "Option B", "Option C"]


# ===========================================================================
# NAVIGATION
# ===========================================================================
def current_card_index() -> int:
    order = st.session_state.review_order
    if not order:
        return 0
    ptr = max(0, min(st.session_state.current_pointer, len(order) - 1))
    st.session_state.current_pointer = ptr
    return order[ptr]


def _schedule_next_round() -> None:
    known   = [i for i, ok in st.session_state.responses.items() if ok]
    unknown = [i for i, ok in st.session_state.responses.items() if not ok]
    unseen  = [i for i in range(len(st.session_state.cards)) if i not in st.session_state.responses]
    weighted = unseen + unknown * 2 + known
    if not weighted:
        weighted = list(range(len(st.session_state.cards)))
    random.shuffle(weighted)
    st.session_state.review_order = weighted
    st.session_state.current_pointer = 0


def move_next() -> None:
    order = st.session_state.review_order
    if st.session_state.current_pointer < len(order) - 1:
        st.session_state.current_pointer += 1
    else:
        _schedule_next_round()
        st.session_state.show_result_summary = True
    st.session_state.show_answer = False
    st.session_state.explain_text = ""


def move_previous() -> None:
    if st.session_state.current_pointer > 0:
        st.session_state.current_pointer -= 1
        st.session_state.show_answer = False
        st.session_state.explain_text = ""


def mark_response(knew: bool) -> None:
    card_idx = current_card_index()
    st.session_state.responses[card_idx] = knew
    if knew:
        st.session_state.current_streak += 1
        st.session_state.best_streak = max(st.session_state.best_streak, st.session_state.current_streak)
    else:
        st.session_state.current_streak = 0
    move_next()


def mastery_stats() -> Dict:
    total = len(st.session_state.cards)
    if total == 0:
        return {"known": 0, "unknown": 0, "answered": 0, "mastery": 0.0, "total": 0}
    known    = sum(1 for v in st.session_state.responses.values() if v)
    unknown  = sum(1 for v in st.session_state.responses.values() if not v)
    answered = known + unknown
    return {"known": known, "unknown": unknown, "answered": answered,
            "mastery": (known / answered) if answered else 0.0, "total": total}


def weak_topics() -> List[Tuple[str, int, int]]:
    topic_correct: Dict[str, int] = {}
    topic_wrong:   Dict[str, int] = {}
    for idx, knew in st.session_state.responses.items():
        if idx < len(st.session_state.cards):
            t = st.session_state.cards[idx].get("topic", "General")
            if knew:
                topic_correct[t] = topic_correct.get(t, 0) + 1
            else:
                topic_wrong[t] = topic_wrong.get(t, 0) + 1
    all_topics = set(list(topic_correct.keys()) + list(topic_wrong.keys()))
    result = [(t, topic_wrong.get(t, 0), topic_wrong.get(t, 0) + topic_correct.get(t, 0)) for t in all_topics]
    result.sort(key=lambda x: x[1] / x[2] if x[2] else 0, reverse=True)
    return result


# ===========================================================================
# PDF REPORT — REPORTLAB (rich) + STDLIB FALLBACK (always works)
# ===========================================================================

def _stdlib_pdf_report() -> bytes:
    """
    Pure-stdlib PDF generator. No third-party dependencies.
    Produces a valid, readable PDF with all study stats.
    """
    stats       = mastery_stats()
    mastery_pct = stats["mastery"] * 100
    now         = datetime.now().strftime("%d %B %Y, %H:%M")
    user_name   = st.session_state.user_name  or "Student"
    user_email  = st.session_state.user_email or "—"

    # ── Build text lines ────────────────────────────────────────────
    lines: List[str] = [
        "FLASHCARD AI — STUDY REPORT",
        "=" * 52,
        "",
        f"Student : {user_name}",
        f"Email   : {user_email}",
        f"Date    : {now}",
        f"Deck    : {stats['total']} cards",
        "",
        "SESSION SUMMARY",
        "-" * 52,
        f"Total Cards    : {stats['total']}",
        f"Cards Answered : {stats['answered']}",
        f"Known          : {stats['known']}",
        f"Unknown        : {stats['unknown']}",
        f"Accuracy       : {mastery_pct:.1f}%",
        f"Best Streak    : {st.session_state.best_streak}",
        "",
    ]

    wt = weak_topics()
    if wt:
        lines += ["WEAK AREAS", "-" * 52]
        for topic, wrong, total in wt[:8]:
            if total and wrong:
                lines.append(f"  {topic:<25} {wrong}/{total} wrong  ({wrong/total*100:.0f}% error)")
        lines.append("")

    lines += ["FLASHCARD REVIEW", "-" * 52, ""]
    for i, card in enumerate(st.session_state.cards):
        resp = st.session_state.responses.get(i)
        resp_str = "Known" if resp is True else ("Unknown" if resp is False else "Not answered")
        diff  = card.get("difficulty", "medium").upper()
        topic = card.get("topic", "General")
        lines.append(f"#{i+1}  [{diff}]  {topic}  ->  {resp_str}")
        # wrap question
        q = card.get("question", "")
        lines.append(f"  Q: {q[:90]}")
        if len(q) > 90:
            lines.append(f"     {q[90:180]}")
        # wrap answer
        a = card.get("answer", "")
        lines.append(f"  A: {a[:90]}")
        if len(a) > 90:
            lines.append(f"     {a[90:180]}")
        lines.append("")

    lines += ["-" * 52, f"Generated by Flashcard AI  |  {now}"]

    # ── Encode into a minimal but valid PDF ─────────────────────────
    def _escape(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    page_w, page_h = 595, 842   # A4 points
    margin_l, margin_t = 50, 800
    line_h = 13
    font_size_title = 13
    font_size_body  = 9

    # We'll split lines across pages
    pages_content: List[bytes] = []
    y = margin_t
    page_lines: List[str] = []

    def _flush_page(pl: List[str]) -> bytes:
        ops = ["BT", f"/F1 {font_size_body} Tf", f"{margin_l} {margin_t} Td"]
        first = True
        for ln in pl:
            sz = font_size_title if ln.startswith("FLASHCARD AI") or ln.startswith("SESSION") or ln.startswith("WEAK") or ln.startswith("FLASHCARD REVIEW") else font_size_body
            if first:
                ops.append(f"/F1 {sz} Tf")
                first = False
            else:
                ops.append(f"0 -{line_h} Td")
                ops.append(f"/F1 {sz} Tf")
            ops.append(f"({_escape(ln)}) Tj")
        ops.append("ET")
        return "\n".join(ops).encode("latin-1", errors="replace")

    page_chunk: List[str] = []
    lines_per_page = 55
    for ln in lines:
        page_chunk.append(ln)
        if len(page_chunk) >= lines_per_page:
            pages_content.append(_flush_page(page_chunk))
            page_chunk = []
    if page_chunk:
        pages_content.append(_flush_page(page_chunk))

    num_pages = len(pages_content)

    # Build PDF binary
    obj_list: List[bytes] = []

    # Obj 1: Catalog
    obj_list.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # Obj 2: Pages (placeholder, filled after)
    kids = " ".join(f"{3 + i*2} 0 R" for i in range(num_pages))
    obj_list.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {num_pages} >>\nendobj\n".encode())

    # Font obj is always last fixed object: obj index = 3 + num_pages*2
    font_obj_num = 3 + num_pages * 2

    for i, content_bytes in enumerate(pages_content):
        page_obj_num    = 3 + i * 2
        content_obj_num = 4 + i * 2
        obj_list.append(
            f"{page_obj_num} 0 obj\n"
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_w} {page_h}] "
            f"/Contents {content_obj_num} 0 R "
            f"/Resources << /Font << /F1 {font_obj_num} 0 R >> >> >>\nendobj\n".encode()
        )
        obj_list.append(
            f"{content_obj_num} 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n".encode()
            + content_bytes + b"\nendstream\nendobj\n"
        )

    obj_list.append(
        (f"{font_obj_num} 0 obj\n"
         "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj\n"
        ).encode()
    )

    # Assemble
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets: List[int] = []
    body = header
    for obj in obj_list:
        offsets.append(len(body))
        body += obj

    total_objs = len(obj_list) + 1  # +1 for obj 0
    xref_pos = len(body)
    xref = f"xref\n0 {total_objs}\n0000000000 65535 f \n".encode()
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()
    trailer = f"trailer\n<< /Size {total_objs} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
    return body + xref + trailer


def _reportlab_pdf_report() -> bytes:
    """Rich styled PDF using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm,
                            title="Flashcard AI — Study Report", author="Flashcard AI")

    C_BG      = colors.HexColor("#080c14")
    C_SURFACE = colors.HexColor("#0f172a")
    C_BORDER  = colors.HexColor("#1e2d4a")
    C_CYAN    = colors.HexColor("#38bdf8")
    C_VIOLET  = colors.HexColor("#818cf8")
    C_GREEN   = colors.HexColor("#22c55e")
    C_YELLOW  = colors.HexColor("#fbbf24")
    C_RED     = colors.HexColor("#ef4444")
    C_TEXT    = colors.HexColor("#e2e8f0")
    C_MUTED   = colors.HexColor("#64748b")

    base = getSampleStyleSheet()
    def ps(name, **kw): return ParagraphStyle(name, parent=base["Normal"], **kw)

    sty_h1   = ps("H1",   fontSize=22, textColor=C_CYAN,   spaceAfter=4,  fontName="Helvetica-Bold", leading=28)
    sty_h2   = ps("H2",   fontSize=13, textColor=C_VIOLET, spaceAfter=3,  fontName="Helvetica-Bold", spaceBefore=10, leading=18)
    sty_q    = ps("Q",    fontSize=9,  textColor=C_TEXT,   spaceAfter=2,  fontName="Helvetica-Bold", leading=13)
    sty_a    = ps("A",    fontSize=9,  textColor=C_GREEN,  spaceAfter=0,  fontName="Helvetica",      leading=13)
    sty_lbl  = ps("Lbl",  fontSize=7,  textColor=C_MUTED,  spaceAfter=1,  fontName="Helvetica",      leading=10)

    story = []

    # Header
    story += [
        Paragraph("Flashcard AI", sty_h1),
        Paragraph("Study Session Report", ps("sub", fontSize=13, textColor=C_VIOLET, fontName="Helvetica", leading=16)),
        Spacer(1, 4*mm),
        HRFlowable(width="100%", thickness=0.5, color=C_BORDER),
        Spacer(1, 3*mm),
    ]

    now        = datetime.now().strftime("%d %B %Y, %H:%M")
    user_name  = st.session_state.user_name  or "Student"
    user_email = st.session_state.user_email or "—"
    stats      = mastery_stats()

    meta = Table(
        [["Student", user_name, "Date", now], ["Email", user_email, "Deck Size", f"{stats['total']} cards"]],
        colWidths=[28*mm, 70*mm, 22*mm, 50*mm]
    )
    meta.setStyle(TableStyle([
        ("FONTNAME",   (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME",   (0,0), (0,-1),  "Helvetica-Bold"),
        ("FONTNAME",   (2,0), (2,-1),  "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("TEXTCOLOR",  (0,0), (0,-1),  C_MUTED), ("TEXTCOLOR", (1,0), (1,-1), C_TEXT),
        ("TEXTCOLOR",  (2,0), (2,-1),  C_MUTED), ("TEXTCOLOR", (3,0), (3,-1), C_TEXT),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [C_SURFACE, C_BG]),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",(0,0), (-1,-1), 8),
    ]))
    story += [meta, Spacer(1, 5*mm)]

    mastery_pct = stats["mastery"] * 100
    story += [
        Paragraph("Session Summary", sty_h2),
        HRFlowable(width="100%", thickness=0.3, color=C_BORDER),
        Spacer(1, 2*mm),
    ]
    stat_table = Table(
        [["Metric", "Value"],
         ["Total Cards", str(stats["total"])], ["Cards Answered", str(stats["answered"])],
         ["Known", str(stats["known"])],       ["Unknown", str(stats["unknown"])],
         ["Accuracy", f"{mastery_pct:.1f}%"],  ["Best Streak", str(st.session_state.best_streak)]],
        colWidths=[80*mm, 90*mm]
    )
    stat_table.setStyle(TableStyle([
        ("FONTNAME",   (0,0), (-1,0),  "Helvetica-Bold"), ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("TEXTCOLOR",  (0,0), (-1,0),  C_CYAN),
        ("TEXTCOLOR",  (0,1), (0,-1),  C_MUTED), ("TEXTCOLOR", (1,1), (1,-1), C_TEXT),
        ("BACKGROUND", (0,0), (-1,0),  C_SURFACE),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [C_BG, C_SURFACE]),
        ("GRID",       (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",(0,0), (-1,-1), 8),
    ]))
    story += [stat_table, Spacer(1, 4*mm)]

    wt = weak_topics()
    if any(w > 0 for _, w, _ in wt):
        story += [Paragraph("Weak Areas Detected", sty_h2), HRFlowable(width="100%", thickness=0.3, color=C_BORDER), Spacer(1, 2*mm)]
        wt_data = [["Topic", "Wrong", "Total", "Error Rate"]]
        for topic, wrong, total in wt[:8]:
            wt_data.append([topic, str(wrong), str(total), f"{wrong/total*100:.0f}%" if total else "—"])
        wt_tbl = Table(wt_data, colWidths=[80*mm, 30*mm, 30*mm, 30*mm])
        wt_tbl.setStyle(TableStyle([
            ("FONTNAME",  (0,0), (-1,0),  "Helvetica-Bold"), ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
            ("FONTSIZE",  (0,0), (-1,-1), 9),
            ("TEXTCOLOR", (0,0), (-1,0),  C_CYAN),
            ("TEXTCOLOR", (0,1), (0,-1),  C_MUTED), ("TEXTCOLOR", (1,1), (1,-1), C_RED),
            ("TEXTCOLOR", (2,1), (2,-1),  C_TEXT),  ("TEXTCOLOR", (3,1), (3,-1), C_YELLOW),
            ("BACKGROUND",(0,0), (-1,0),  C_SURFACE),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [C_BG, C_SURFACE]),
            ("GRID",      (0,0), (-1,-1), 0.3, C_BORDER),
            ("TOPPADDING",(0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",(0,0),(-1,-1), 8),
        ]))
        story += [wt_tbl, Spacer(1, 4*mm)]

    story += [PageBreak(), Paragraph("Complete Flashcard Review", sty_h2),
              HRFlowable(width="100%", thickness=0.3, color=C_BORDER), Spacer(1, 3*mm)]

    for i, card in enumerate(st.session_state.cards):
        resp     = st.session_state.responses.get(i)
        resp_str = "Known" if resp is True else ("Unknown" if resp is False else "Not answered")
        resp_col = C_GREEN if resp is True else (C_RED if resp is False else C_MUTED)
        diff     = card.get("difficulty", "medium")
        topic    = card.get("topic", "General")
        diff_col = {"easy": C_GREEN, "medium": C_YELLOW, "hard": C_RED}.get(diff, C_MUTED)

        ct = Table([
            [Paragraph(f"#{i+1} — {topic}", sty_lbl),
             Paragraph(diff.upper(), ps(f"d{i}", fontSize=7, textColor=diff_col, fontName="Helvetica-Bold")),
             Paragraph(resp_str,    ps(f"r{i}", fontSize=7, textColor=resp_col,  fontName="Helvetica-Bold"))],
            [Paragraph(card.get("question", ""), sty_q), "", ""],
            [Paragraph(card.get("answer",   ""), sty_a), "", ""],
        ], colWidths=[110*mm, 30*mm, 30*mm])
        ct.setStyle(TableStyle([
            ("SPAN",         (0,1), (2,1)), ("SPAN", (0,2), (2,2)),
            ("BACKGROUND",   (0,0), (-1,-1), C_SURFACE),
            ("TOPPADDING",   (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",  (0,0), (-1,-1), 8), ("RIGHTPADDING",  (0,0), (-1,-1), 8),
            ("LINEBELOW",    (0,0), (-1,0),  0.3, C_BORDER),
        ]))
        story += [ct, Spacer(1, 2.5*mm)]

    story += [
        Spacer(1, 6*mm),
        HRFlowable(width="100%", thickness=0.3, color=C_BORDER),
        Paragraph(f"Generated by Flashcard AI  |  {now}",
                  ps("footer", fontSize=7, textColor=C_MUTED, fontName="Helvetica", alignment=1)),
    ]

    doc.build(story)
    return buf.getvalue()


def generate_pdf_report() -> Tuple[bytes, str]:
    """
    Returns (pdf_bytes, mime_type).
    Uses reportlab if available, falls back to stdlib PDF otherwise.
    """
    if _REPORTLAB_AVAILABLE:
        try:
            return _reportlab_pdf_report(), "application/pdf"
        except Exception as e:
            # Log to session, continue to fallback
            st.session_state.last_error = f"reportlab error (using fallback): {e}"
    return _stdlib_pdf_report(), "application/pdf"


# ===========================================================================
# SIDEBAR
# ===========================================================================
def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## ⚡ Flashcard AI")
        st.caption("PDF → practice-ready decks with spaced repetition.")

        if _get_api_key():
            st.markdown('<span class="status-pill status-ok"><span class="dot dot-pulse"></span> Groq connected</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-pill status-err"><span class="dot"></span> API key missing</span>', unsafe_allow_html=True)
            st.caption("Set `GROQ_API_KEY` in your `.env` file.")

        if not _REPORTLAB_AVAILABLE:
            st.markdown('<div class="warn-box">⚠️ <b>reportlab not installed.</b><br>PDF will use basic format.<br>Run: <code>pip install reportlab</code></div>', unsafe_allow_html=True)

        st.markdown("---")

        if st.session_state.cards:
            st.markdown("### 🎛 Study Controls")
            all_topics = ["All"] + sorted(set(c.get("topic", "General") for c in st.session_state.cards))
            topic = st.selectbox("Filter by topic", all_topics,
                                 index=all_topics.index(st.session_state.topic_filter) if st.session_state.topic_filter in all_topics else 0)
            if topic != st.session_state.topic_filter:
                st.session_state.topic_filter = topic
                st.session_state.current_pointer = 0
                st.session_state.show_answer = False
                _rebuild_review_order()

            mode_options = ["Normal", "Unknown First", "Hard Only", "Review Mistakes"]
            cur_idx = mode_options.index(st.session_state.study_mode) if st.session_state.study_mode in mode_options else 0
            mode = st.selectbox("Study mode", mode_options, index=cur_idx)
            if mode != st.session_state.study_mode:
                st.session_state.study_mode = mode
                st.session_state.current_pointer = 0
                st.session_state.show_answer = False
                _rebuild_review_order()

            shuffle = st.toggle("Shuffle cards", value=st.session_state.shuffle)
            if shuffle != st.session_state.shuffle:
                st.session_state.shuffle = shuffle
                _rebuild_review_order()

            st.markdown("---")

            mistakes = [i for i, ok in st.session_state.responses.items() if not ok]
            if mistakes:
                if st.button(f"🔁 Practice {len(mistakes)} Mistake(s)", use_container_width=True):
                    order = mistakes * 2
                    random.shuffle(order)
                    st.session_state.review_order = order
                    st.session_state.current_pointer = 0
                    st.session_state.show_answer = False
                    st.rerun()

            if st.button("🔄 Reset Progress", use_container_width=True):
                st.session_state.responses = {}
                st.session_state.current_pointer = 0
                st.session_state.show_answer = False
                st.session_state.current_streak = 0
                st.session_state.best_streak = 0
                _rebuild_review_order()
                st.rerun()

            st.markdown("---")
            streak = st.session_state.current_streak
            if streak >= 3:
                st.markdown(f'<span class="streak-badge">🔥 {streak} card streak!</span>', unsafe_allow_html=True)
                st.markdown("")

            st.markdown("### 👤 Your Info (for PDF)")
            name  = st.text_input("Name",  value=st.session_state.user_name,  placeholder="Your name",      label_visibility="collapsed")
            email = st.text_input("Email", value=st.session_state.user_email, placeholder="your@email.com", label_visibility="collapsed")
            if name  != st.session_state.user_name:  st.session_state.user_name  = name
            if email != st.session_state.user_email: st.session_state.user_email = email

            st.markdown("---")
            payload = {"flashcards": st.session_state.cards}
            st.download_button("💾 Save Deck (JSON)", data=json.dumps(payload, indent=2),
                               file_name="flashcard_deck.json", mime="application/json", use_container_width=True)

        if st.session_state.last_error and st.session_state.last_input_text:
            st.markdown("### ⚠️ Last Generation Failed")
            err = st.session_state.last_error
            st.caption(err[:120] + "…" if len(err) > 120 else err)
            if st.button("🔁 Retry Last Request", use_container_width=True):
                st.session_state.generation_pending = True
                st.session_state.last_error = ""
                st.rerun()

        st.markdown("### 📖 How to use")
        st.markdown("1. Upload PDF or paste notes\n2. Generate cards\n3. Study across tabs\n4. Track progress & export report")


# ===========================================================================
# INPUT PANEL
# ===========================================================================
def input_panel() -> str:
    st.markdown("<div class='app-title'>Flashcard AI</div>", unsafe_allow_html=True)
    st.markdown("<div class='app-subtitle'>Turn any PDF or notes into a smart, adaptive study deck.</div>", unsafe_allow_html=True)

    col_file, col_text = st.columns([1, 1], gap="large")
    with col_file:
        uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"], label_visibility="collapsed")
        if uploaded_file:
            st.markdown(f"<div style='color:#38bdf8;font-size:0.85rem;'>📄 {uploaded_file.name}</div>", unsafe_allow_html=True)
            with st.spinner("⏳ Extracting text from PDF…"):
                text, pdf_warn = extract_pdf_text(uploaded_file)
            if pdf_warn:
                st.markdown(f"<div class='warn-box'>⚠️ {pdf_warn}</div>", unsafe_allow_html=True)
            if not text:
                st.error("Could not extract text. Try pasting the content instead.")
                return ""
            st.success(f"✅ Extracted ~{len(text):,} characters.")
            st.markdown("**Or load a saved deck:**")
            deck_file = st.file_uploader("Load JSON deck", type=["json"], label_visibility="collapsed", key="deck_loader")
            if deck_file:
                try:
                    data = json.load(deck_file)
                    cards = _sanitise_cards(data.get("flashcards", []))
                    if cards:
                        reset_learning_state(cards)
                        st.success(f"✅ Loaded {len(cards)} cards from saved deck.")
                        st.rerun()
                    else:
                        st.error("No valid cards found in file.")
                except Exception as e:
                    st.error(f"Could not load deck: {e}")
            return text

    with col_text:
        pasted = st.text_area("Or paste your notes", height=160,
                              placeholder="Paste chapter notes, lecture slides, or any study material…",
                              label_visibility="collapsed")
        deck_file2 = st.file_uploader("Or load a saved deck (JSON)", type=["json"],
                                      label_visibility="collapsed", key="deck_loader2")
        if deck_file2:
            try:
                data = json.load(deck_file2)
                cards = _sanitise_cards(data.get("flashcards", []))
                if cards:
                    reset_learning_state(cards)
                    st.success(f"✅ Loaded {len(cards)} cards.")
                    st.rerun()
            except Exception as e:
                st.error(f"Could not load deck: {e}")
        return pasted.strip()


# ===========================================================================
# GENERATION CONTROLS
# ===========================================================================
def generation_controls(raw_text: str) -> None:
    col_slider, col_btn = st.columns([2, 1], gap="medium")
    with col_slider:
        num_cards = st.slider("Number of cards to generate", min_value=5, max_value=40, value=10, step=5)
    with col_btn:
        st.write("")
        generate_clicked = st.button("⚡ Generate Flashcards", type="primary", use_container_width=True)

    should_generate = generate_clicked or st.session_state.get("generation_pending", False)
    if not should_generate:
        return

    st.session_state.generation_pending = False

    if not _get_api_key():
        st.error("⚠️ Missing API key. Add `GROQ_API_KEY` to your `.env` file.")
        return

    text_to_use = raw_text or st.session_state.last_input_text
    if not text_to_use:
        st.error("Please upload a PDF or paste some text first.")
        return

    truncated_text, trunc_warn = _truncate_input(text_to_use)
    if trunc_warn:
        st.markdown(f"<div class='warn-box'>⚠️ {trunc_warn}</div>", unsafe_allow_html=True)

    st.session_state.last_input_text = text_to_use
    st.session_state.last_num_cards  = num_cards

    status_box   = st.empty()
    progress_bar = st.progress(0)
    try:
        status_box.info("🧠 Step 1 / 3 — Analysing content…");   progress_bar.progress(15)
        status_box.info("🤖 Step 2 / 3 — Calling Groq API…");     progress_bar.progress(40)
        cards = _cached_generate(truncated_text, num_cards)
        status_box.info("🃏 Step 3 / 3 — Building your deck…");    progress_bar.progress(85)
        time.sleep(0.2)
        reset_learning_state(cards)
        progress_bar.progress(100)
        status_box.success(f"✅ Generated **{len(cards)} flashcards** — start practising below!")
    except RuntimeError as e:
        progress_bar.empty()
        err_str = str(e)
        st.session_state.last_error = err_str
        status_box.error(f"❌ {err_str}")
        st.warning("Use **Retry Last Request** in the sidebar to try again.")
    except Exception as e:
        progress_bar.empty()
        err_str = f"{type(e).__name__}: {e}"
        st.session_state.last_error = err_str
        status_box.error(f"❌ Unexpected error: {err_str}")


# ===========================================================================
# PROGRESS BAR + METRICS
# ===========================================================================
def render_empty_state() -> None:
    st.markdown("""
    <div class="empty-card">
        <div style="font-size:2.5rem;margin-bottom:0.75rem;">📚</div>
        <div style="font-size:1.1rem;color:#64748b;">
            Upload a PDF or paste your notes, then click <strong>Generate Flashcards</strong> to begin.
        </div>
    </div>""", unsafe_allow_html=True)


def render_progress() -> None:
    stats = mastery_stats()
    total = stats["total"]
    progress_val = stats["answered"] / total if total else 0
    mastery_pct  = stats["mastery"] * 100
    mc = "green" if mastery_pct >= 70 else ("yellow" if mastery_pct >= 40 else "red")

    st.progress(progress_val)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(f'<div class="metric-box"><div class="metric-label">Mastery</div><div class="metric-value {mc}">{mastery_pct:.0f}%</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-box"><div class="metric-label">Known ✅</div><div class="metric-value green">{stats["known"]}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-box"><div class="metric-label">Unknown ❌</div><div class="metric-value red">{stats["unknown"]}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-box"><div class="metric-label">Streak 🔥</div><div class="metric-value yellow">{st.session_state.current_streak}</div></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="metric-box"><div class="metric-label">Total Cards</div><div class="metric-value blue">{total}</div></div>', unsafe_allow_html=True)


# ===========================================================================
# FLASHCARD TAB
# ===========================================================================
def render_flashcard_tab() -> None:
    if not st.session_state.review_order:
        st.warning("No cards match the current filter/mode. Switch topic or study mode in the sidebar.")
        return

    card_idx = current_card_index()
    card     = st.session_state.cards[card_idx]
    total    = len(st.session_state.review_order)
    position = st.session_state.current_pointer + 1
    diff     = card.get("difficulty", "medium")
    topic    = card.get("topic", "General")
    response = st.session_state.responses.get(card_idx)
    card_status = (
        " · <span style='color:#22c55e'>✓ Known</span>"   if response is True  else
        " · <span style='color:#ef4444'>✗ Unknown</span>" if response is False else ""
    )

    st.markdown(
        f"<div class='card-counter'>Card {position} / {total}"
        f"<span class='mode-tag'>{st.session_state.study_mode}</span>"
        f"<span class='topic-tag'>{topic}</span>{card_status}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"""
    <div class="glass-card">
        <div class="card-label">Question</div>
        <div class="card-text">{card.get('question', '')}</div>
        <span class="badge badge-{diff}">{diff}</span>
    </div>""", unsafe_allow_html=True)

    if st.session_state.show_answer:
        st.markdown(f"""
        <div class="answer-card">
            <div class="answer-label">Answer</div>
            <div class="card-text">{card.get('answer', '')}</div>
        </div>""", unsafe_allow_html=True)
        if st.session_state.explain_text:
            st.markdown(f"""
            <div class="explain-box">
                <div class="explain-label">🔍 Deeper Explanation</div>
                <div class="explain-text">{st.session_state.explain_text}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
    n1, n2, n3, n4, n5 = st.columns(5)
    with n1:
        if st.button("← Previous",  use_container_width=True): move_previous(); st.rerun()
    with n2:
        lbl = "🙈 Hide Answer" if st.session_state.show_answer else "👁 Show Answer"
        if st.button(lbl, use_container_width=True):
            st.session_state.show_answer = not st.session_state.show_answer
            if not st.session_state.show_answer: st.session_state.explain_text = ""
            st.rerun()
    with n3:
        if st.button("✅ I knew this", use_container_width=True): mark_response(True);  st.rerun()
    with n4:
        if st.button("❌ Didn't know", use_container_width=True): mark_response(False); st.rerun()
    with n5:
        if st.button("Next →",       use_container_width=True): move_next(); st.rerun()

    if st.session_state.show_answer:
        col_exp, _ = st.columns([1, 3])
        with col_exp:
            if st.button("🔍 Explain Better", use_container_width=True):
                with st.spinner("Getting a deeper explanation…"):
                    st.session_state.explain_text = _cached_explain(card["question"], card["answer"])
                st.rerun()


# ===========================================================================
# MCQ TAB
# ===========================================================================
def render_mcq_tab() -> None:
    if not st.session_state.review_order:
        st.warning("No cards available.")
        return

    card_idx = current_card_index()
    card     = st.session_state.cards[card_idx]
    diff     = card.get("difficulty", "medium")
    topic    = card.get("topic", "General")
    total    = len(st.session_state.review_order)
    position = st.session_state.current_pointer + 1

    st.markdown(
        f"<div class='card-counter'>Question {position} / {total}"
        f"<span class='mode-tag'>MCQ</span><span class='topic-tag'>{topic}</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"""
    <div class="glass-card">
        <div class="card-label">Multiple Choice</div>
        <div class="card-text">{card.get('question', '')}</div>
        <span class="badge badge-{diff}">{diff}</span>
    </div>""", unsafe_allow_html=True)

    if card_idx not in st.session_state.mcq_options:
        with st.spinner("Generating options…"):
            distractors = _cached_mcq_distractors(card["question"], card["answer"])
        options = [card["answer"]] + distractors
        random.shuffle(options)
        st.session_state.mcq_options[card_idx] = options

    options  = st.session_state.mcq_options[card_idx]
    selected = st.session_state.mcq_selected.get(card_idx)

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    if selected is None:
        for opt in options:
            if st.button(opt, key=f"mcq_{card_idx}_{opt}", use_container_width=True):
                st.session_state.mcq_selected[card_idx] = opt
                mark_response(opt == card["answer"])
                st.rerun()
    else:
        correct_answer = card["answer"]
        for opt in options:
            if opt == correct_answer:
                cls, prefix = "mcq-option mcq-correct", "✅ "
            elif opt == selected and opt != correct_answer:
                cls, prefix = "mcq-option mcq-wrong", "❌ "
            else:
                cls, prefix = "mcq-option", "    "
            st.markdown(f'<div class="{cls}">{prefix}{opt}</div>', unsafe_allow_html=True)

        if selected == correct_answer:
            st.success("🎉 Correct!")
        else:
            st.error(f"Wrong. The correct answer was: **{correct_answer}**")

        col_next, col_exp, _ = st.columns([1, 1, 2])
        with col_next:
            if st.button("Next Question →", use_container_width=True): move_next(); st.rerun()
        with col_exp:
            if st.button("🔍 Explain", use_container_width=True):
                with st.spinner("Explaining…"):
                    st.session_state.explain_text = _cached_explain(card["question"], card["answer"])
                st.rerun()
        if st.session_state.explain_text:
            st.markdown(f"""
            <div class="explain-box">
                <div class="explain-label">🔍 Deeper Explanation</div>
                <div class="explain-text">{st.session_state.explain_text}</div>
            </div>""", unsafe_allow_html=True)


# ===========================================================================
# EXAM TAB
# ===========================================================================
def render_exam_tab() -> None:
    cards = st.session_state.cards
    if not cards:
        st.warning("Generate cards first.")
        return

    if not st.session_state.exam_active and not st.session_state.exam_finished:
        st.markdown("<div class='section-heading'>⏱ Exam Mode Setup</div>", unsafe_allow_html=True)
        col_t, col_s = st.columns([1, 1])
        with col_t:
            duration = st.selectbox("Time limit", [2, 5, 10, 15, 20, 30], index=1, format_func=lambda x: f"{x} minutes")
        with col_s:
            subset = st.selectbox("Cards to include", ["All cards", "Hard only", "Unknown only"])

        if st.button("🚀 Start Exam", type="primary", use_container_width=True):
            if subset == "Hard only":
                order = [i for i, c in enumerate(cards) if c.get("difficulty") == "hard"] or list(range(len(cards)))
            elif subset == "Unknown only":
                order = [i for i, ok in st.session_state.responses.items() if not ok] or list(range(len(cards)))
            else:
                order = list(range(len(cards)))
            random.shuffle(order)
            st.session_state.exam_order      = order
            st.session_state.exam_pointer    = 0
            st.session_state.exam_responses  = {}
            st.session_state.exam_active     = True
            st.session_state.exam_finished   = False
            st.session_state.exam_start_time = time.time()
            st.session_state.exam_duration_s = duration * 60
            st.rerun()
        return

    if st.session_state.exam_finished:
        _render_exam_results(); return

    elapsed   = time.time() - st.session_state.exam_start_time
    remaining = max(0, st.session_state.exam_duration_s - elapsed)
    mins, secs = int(remaining // 60), int(remaining % 60)

    if remaining <= 0:
        st.session_state.exam_active = False; st.session_state.exam_finished = True; st.rerun()

    timer_cls = "exam-timer danger" if remaining < 60 else ("exam-timer warning" if remaining < 120 else "exam-timer")
    order   = st.session_state.exam_order
    pointer = st.session_state.exam_pointer

    if pointer >= len(order):
        st.session_state.exam_active = False; st.session_state.exam_finished = True; st.rerun()

    card_idx = order[pointer]
    card     = cards[card_idx]
    answered = len(st.session_state.exam_responses)
    total    = len(order)

    tc, pc, _ = st.columns([1, 2, 1])
    with tc: st.markdown(f'<div class="{timer_cls}">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
    with pc:
        st.progress(pointer / total if total else 0)
        st.caption(f"Question {pointer+1} / {total}  ·  {answered} answered")

    st.markdown(f"""
    <div class="glass-card" style="margin-top:0.6rem;">
        <div class="card-label">Exam Question {pointer+1}</div>
        <div class="card-text">{card.get('question', '')}</div>
        <span class="badge badge-{card.get('difficulty','medium')}">{card.get('difficulty','medium')}</span>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    ea, eb, skip_col = st.columns([1, 1, 2])
    with ea:
        if st.button("✅ I knew this", use_container_width=True, key="exam_know"):
            st.session_state.exam_responses[card_idx] = True
            st.session_state.exam_pointer += 1; st.rerun()
    with eb:
        if st.button("❌ Didn't know", use_container_width=True, key="exam_nope"):
            st.session_state.exam_responses[card_idx] = False
            st.session_state.exam_pointer += 1; st.rerun()
    with skip_col:
        cs, ce = st.columns([1, 1])
        with cs:
            if st.button("Skip →", use_container_width=True): st.session_state.exam_pointer += 1; st.rerun()
        with ce:
            if st.button("Finish Exam", use_container_width=True):
                st.session_state.exam_active = False; st.session_state.exam_finished = True; st.rerun()

    time.sleep(1)
    st.rerun()


def _render_exam_results() -> None:
    responses = st.session_state.exam_responses
    order     = st.session_state.exam_order
    total     = len(order)
    answered  = len(responses)
    known     = sum(1 for v in responses.values() if v)
    unknown   = sum(1 for v in responses.values() if not v)
    accuracy  = (known / answered * 100) if answered else 0
    elapsed   = min(time.time() - (st.session_state.exam_start_time or time.time()), st.session_state.exam_duration_s)
    mins, secs = int(elapsed // 60), int(elapsed % 60)
    acc_color = "green" if accuracy >= 70 else ("yellow" if accuracy >= 40 else "red")

    st.markdown("<div class='result-card'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:1.6rem;font-weight:700;color:#38bdf8;margin-bottom:0.5rem;'>🎓 Exam Complete</div>", unsafe_allow_html=True)
    st.progress(known / total if total else 0)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-box"><div class="metric-label">Score</div><div class="metric-value {acc_color}">{accuracy:.0f}%</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-box"><div class="metric-label">Correct</div><div class="metric-value green">{known}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-box"><div class="metric-label">Wrong</div><div class="metric-value red">{unknown}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-box"><div class="metric-label">Time Used</div><div class="metric-value blue">{mins:02d}:{secs:02d}</div></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    missed_idx = [i for i, ok in responses.items() if not ok]
    if missed_idx:
        st.markdown(f"<div class='section-heading'>❌ Cards to Review ({len(missed_idx)})</div>", unsafe_allow_html=True)
        for i in missed_idx[:10]:
            card = st.session_state.cards[i]
            st.markdown(f'<div class="analytics-row"><span style="color:#e2e8f0;">{card.get("question","")}</span><span style="color:#64748b;font-size:0.8rem;">{card.get("topic","")}</span></div>', unsafe_allow_html=True)

    col_retry, col_close = st.columns([1, 1])
    with col_retry:
        if st.button("🔁 Retry Exam", use_container_width=True):
            st.session_state.exam_finished = False; st.session_state.exam_active = False; st.rerun()
    with col_close:
        if st.button("✅ Done", use_container_width=True, type="primary"):
            for idx, knew in responses.items():
                st.session_state.responses[idx] = knew
            st.session_state.exam_finished = False; st.session_state.exam_active = False; st.rerun()


# ===========================================================================
# ANALYTICS TAB
# ===========================================================================
def render_analytics_tab() -> None:
    stats = mastery_stats()
    mastery_pct = stats["mastery"] * 100
    mc = "green" if mastery_pct >= 70 else ("yellow" if mastery_pct >= 40 else "red")

    st.markdown("<div class='section-heading'>📊 Analytics Dashboard</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-box"><div class="metric-label">Overall Accuracy</div><div class="metric-value {mc}">{mastery_pct:.1f}%</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-box"><div class="metric-label">Best Streak 🔥</div><div class="metric-value yellow">{st.session_state.best_streak}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-box"><div class="metric-label">Cards Answered</div><div class="metric-value blue">{stats["answered"]}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-box"><div class="metric-label">Remaining</div><div class="metric-value">{stats["total"] - stats["answered"]}</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-heading'>Difficulty Breakdown</div>", unsafe_allow_html=True)
    for diff in ("easy", "medium", "hard"):
        diff_cards = [i for i, c in enumerate(st.session_state.cards) if c.get("difficulty") == diff]
        correct    = sum(1 for i in diff_cards if st.session_state.responses.get(i) is True)
        total_d    = len(diff_cards)
        pct        = (correct / total_d * 100) if total_d else 0
        dc         = "green" if diff == "easy" else ("yellow" if diff == "medium" else "red")
        color      = '#22c55e' if dc == 'green' else ('#fbbf24' if dc == 'yellow' else '#ef4444')
        st.markdown(f'<div class="analytics-row"><span style="text-transform:capitalize;font-weight:600;">{diff}</span><span>{correct} / {total_d} correct</span><span style="color:{color};font-weight:600;">{pct:.0f}%</span></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    topic_stats: Dict[str, Dict] = {}
    for i, card in enumerate(st.session_state.cards):
        t = card.get("topic", "General")
        if t not in topic_stats:
            topic_stats[t] = {"correct": 0, "wrong": 0, "unseen": 0}
        r = st.session_state.responses.get(i)
        if r is True:    topic_stats[t]["correct"] += 1
        elif r is False: topic_stats[t]["wrong"]   += 1
        else:            topic_stats[t]["unseen"]  += 1

    st.markdown("<div class='section-heading'>Topic Breakdown</div>", unsafe_allow_html=True)
    for t, ts in sorted(topic_stats.items()):
        answered = ts["correct"] + ts["wrong"]
        pct      = (ts["correct"] / answered * 100) if answered else 0
        tc       = "green" if pct >= 70 else ("yellow" if pct >= 40 else "red")
        color    = '#22c55e' if tc == 'green' else ('#fbbf24' if tc == 'yellow' else '#ef4444')
        st.markdown(f'<div class="analytics-row"><span style="font-weight:600;">{t}</span><span style="color:#64748b;">{ts["correct"]}✅ {ts["wrong"]}❌ {ts["unseen"]} unseen</span><span style="color:{color};font-weight:600;">{pct:.0f}%</span></div>', unsafe_allow_html=True)

    wt = weak_topics()
    if wt:
        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-heading'>⚠️ Weak Areas</div>", unsafe_allow_html=True)
        for topic, wrong, total in wt[:5]:
            if wrong == 0: continue
            rate = wrong / total * 100
            st.markdown(f'<div class="weak-topic-row"><span style="font-weight:600;">{topic}</span><span style="color:#ef4444;">{wrong} wrong / {total} total · {rate:.0f}% error rate</span></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-heading'>📄 Download Report</div>", unsafe_allow_html=True)

    if not _REPORTLAB_AVAILABLE:
        st.markdown('<div class="warn-box">⚠️ <code>reportlab</code> not installed — PDF will use basic format. Run <code>pip install reportlab</code> for the full styled version.</div>', unsafe_allow_html=True)

    if st.button("📥 Generate PDF Report", use_container_width=True):
        with st.spinner("Generating PDF report…"):
            pdf_bytes, mime = generate_pdf_report()
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        label = "⬇ Download PDF Report" + (" (styled)" if _REPORTLAB_AVAILABLE else " (basic)")
        st.download_button(label=label, data=pdf_bytes, file_name=f"flashcard_report_{ts}.pdf",
                           mime=mime, use_container_width=True)


# ===========================================================================
# RESULT SUMMARY
# ===========================================================================
def render_result_summary() -> None:
    stats = mastery_stats()
    mastery_pct = stats["mastery"] * 100
    mc = "green" if mastery_pct >= 70 else ("yellow" if mastery_pct >= 40 else "red")

    st.markdown('<div class="result-card"><div style="font-size:1.5rem;font-weight:700;color:#38bdf8;margin-bottom:0.8rem;">🏁 Deck Complete!</div></div>', unsafe_allow_html=True)
    st.progress(stats["known"] / stats["total"] if stats["total"] else 0)
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="metric-box"><div class="metric-label">Final Accuracy</div><div class="metric-value {mc}">{mastery_pct:.0f}%</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-box"><div class="metric-label">Known ✅</div><div class="metric-value green">{stats["known"]}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-box"><div class="metric-label">Unknown ❌</div><div class="metric-value red">{stats["unknown"]}</div></div>', unsafe_allow_html=True)

    wt = [(t, w, tot) for t, w, tot in weak_topics() if w > 0]
    if wt:
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-heading'>⚠️ Areas to Revisit</div>", unsafe_allow_html=True)
        for topic, wrong, total in wt[:4]:
            st.markdown(f'<div class="weak-topic-row"><span>{topic}</span><span style="color:#ef4444;">{wrong/total*100:.0f}% error rate</span></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("🔁 Study Again", use_container_width=True, type="primary"):
            st.session_state.show_result_summary = False
            st.session_state.responses = {}
            st.session_state.current_streak = 0
            _rebuild_review_order()
            st.rerun()
    with col_b:
        if st.button("📥 Download PDF Report", use_container_width=True):
            with st.spinner("Generating PDF…"):
                pdf_bytes, mime = generate_pdf_report()
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            st.download_button("⬇ Save Report", data=pdf_bytes,
                               file_name=f"flashcard_report_{ts}.pdf", mime=mime, use_container_width=True)
    if st.button("Continue Studying →", use_container_width=True):
        st.session_state.show_result_summary = False
        st.rerun()


# ===========================================================================
# EXPORT SECTION
# ===========================================================================
def export_section() -> None:
    if not st.session_state.cards:
        return
    st.markdown("---")
    col_json, col_csv, col_pdf = st.columns([1, 1, 1])
    payload = {"flashcards": st.session_state.cards}

    with col_json:
        st.download_button("⬇ Export JSON", data=json.dumps(payload, indent=2),
                           file_name="flashcards.json", mime="application/json", use_container_width=True)
    with col_csv:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["question", "answer", "difficulty", "topic"])
        writer.writeheader(); writer.writerows(st.session_state.cards)
        st.download_button("⬇ Export CSV", data=buf.getvalue(),
                           file_name="flashcards.csv", mime="text/csv", use_container_width=True)
    with col_pdf:
        if st.button("📄 PDF Report", use_container_width=True):
            with st.spinner("Generating PDF…"):
                pdf_bytes, mime = generate_pdf_report()
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            st.download_button("⬇ Save PDF", data=pdf_bytes,
                               file_name=f"flashcard_report_{ts}.pdf", mime=mime, use_container_width=True)
    st.caption(f"Deck: **{len(st.session_state.cards)}** cards · {len(set(c.get('topic','General') for c in st.session_state.cards))} topics"
               + ("" if _REPORTLAB_AVAILABLE else "  |  ⚠️ Install `reportlab` for styled PDF"))


# ===========================================================================
# MAIN
# ===========================================================================
def main() -> None:
    inject_styles()
    init_state()
    render_sidebar()

    raw_text = input_panel()
    generation_controls(raw_text)
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    if not st.session_state.cards:
        render_empty_state()
        return

    render_progress()
    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    if st.session_state.show_result_summary:
        render_result_summary()
        return

    tab1, tab2, tab3, tab4 = st.tabs(["🃏 Flashcards", "❓ Multiple Choice", "⏱ Exam Mode", "📊 Analytics"])
    with tab1: render_flashcard_tab()
    with tab2: render_mcq_tab()
    with tab3: render_exam_tab()
    with tab4: render_analytics_tab()

    export_section()


if __name__ == "__main__":
    main()