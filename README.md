<div align="center">

<!-- Animated title -->
<img src="https://readme-typing-svg.demolab.com?font=Space+Grotesk&weight=700&size=36&duration=3000&pause=1000&color=38BDF8&center=true&vCenter=true&width=600&lines=⚡+Flashcard+AI;Active+Recall+%2B+Spaced+Repetition;Built+for+Cuemath+Build+Challenge" alt="Typing SVG" />

<br/>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036?style=for-the-badge&logo=meta&logoColor=white)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)

<br/>

> **Turn any PDF into a smart, adaptive study deck in seconds.**  
> Powered by Groq + Llama 3.3-70B. No account needed.

<br/>

<!-- Demo gif placeholder — replace with your own recording -->
<img src="https://via.placeholder.com/900x480/080c14/38bdf8?text=App+Screenshot+Here" width="900" alt="Flashcard AI Demo" style="border-radius:16px"/>

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🃏 Smart Flashcards
- PDF → deck in seconds via Groq API
- Cards cover definitions, relationships, edge cases & examples  
- Difficulty tags: Easy / Medium / Hard
- Topic auto-tagging per card
- **Explain Better** — AI-powered deeper explanations

</td>
<td width="50%">

### 📊 Spaced Repetition Engine
- Unknown cards appear 2× more often
- Study modes: Normal · Unknown First · Hard Only · Review Mistakes
- Topic filter — study one subject at a time
- Shuffle toggle
- Live mastery % + streak counter 🔥

</td>
</tr>
<tr>
<td>

### ❓ Multiple Choice Mode
- AI generates 3 plausible wrong distractors per card
- Color-coded feedback (correct = green, wrong = red)
- Cached — no duplicate API calls on revisit
- Counts toward your mastery score

</td>
<td>

### ⏱ Exam Mode
- Configurable timer (2 – 30 minutes)
- Card subsets: All / Hard only / Unknown only
- No answer previews — exam conditions
- Full result screen with missed-card review
- Merges exam results into main progress

</td>
</tr>
<tr>
<td>

### 📈 Analytics Dashboard
- Accuracy % · Best streak · Answered / Remaining
- Difficulty breakdown (easy / medium / hard)
- Topic breakdown table
- Weak areas panel (sorted by error rate)

</td>
<td>

### 📄 PDF Report Export
- Styled report via **reportlab** (dark theme matching app)
- Fallback to stdlib PDF if reportlab not installed *(no crash)*
- Includes: student info · summary stats · weak areas · full card list
- Generated on-demand, never slows the app

</td>
</tr>
</table>

---

## 🚀 Quick Start

### 1 — Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/flashcard-ai.git
cd flashcard-ai
pip install -r requirements.txt
```

### 2 — Get your free Groq API key

Sign up at [console.groq.com](https://console.groq.com) — no credit card, generous free tier.

```bash
cp .env.example .env
# Open .env and paste your key:
# GROQ_API_KEY=gsk_...
```

### 3 — Run

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. Done.

---

## 🛠 Installation Notes

### Fix: `ModuleNotFoundError: No module named 'reportlab'`

```bash
pip install reportlab
```

If you can't install reportlab (restricted environment), the app automatically falls back to a pure-stdlib PDF generator. You'll still get a valid, downloadable PDF — just without the styled dark theme.

### Full dependency list

| Package | Purpose | Required? |
|---|---|---|
| `streamlit` | UI framework | ✅ Yes |
| `groq` | Llama 3.3-70B API | ✅ Yes |
| `python-dotenv` | Load `.env` file | ✅ Yes |
| `pdfplumber` | PDF text extraction (primary) | Recommended |
| `PyMuPDF` | PDF extraction (fallback 1) | Recommended |
| `pypdf` | PDF extraction (fallback 2) | Recommended |
| `reportlab` | Styled PDF report | Optional ⚠️ |

---

## 🏗 Architecture

```
flashcard-ai/
├── app.py               # Single-file Streamlit app (all logic + UI)
├── requirements.txt
├── .env.example
└── README.md
```

### Data flow

```
PDF / Text Input
      │
      ▼
_cached_extract_pdf()     ← st.cache_data (keyed by file bytes)
      │
      ▼
_cached_generate()        ← Groq API · 3-attempt retry · JSON validation
      │
      ▼
Session State (cards[])   ← Never resets on rerun
      │
      ├──► Flashcard Tab    (flip · known/unknown · spaced repetition)
      ├──► MCQ Tab          (_cached_mcq_distractors · 4-option quiz)
      ├──► Exam Tab         (countdown timer · no previews · result screen)
      └──► Analytics Tab    (topic breakdown · weak areas · PDF export)
```

---

## 🔧 Key Engineering Decisions

| Decision | Rationale |
|---|---|
| Single `app.py` | Easier to deploy on any platform — no import path issues |
| `@st.cache_data` on all API calls | Same input never hits Groq twice — instant on rerun |
| 3-attempt retry + exponential back-off | Groq occasionally returns malformed JSON — must handle gracefully |
| `_safe_parse_json()` strips fences + finds outermost `{}` | Handles every malformed response pattern we observed |
| `reportlab` optional + stdlib fallback | App never crashes from a missing dependency |
| Deck saved as JSON | Portable across sessions, devices, and users — no database needed |
| Session state initialized with `if key not in` | Never clobbers existing data on rerun |

---

## 🚢 Deployment

### Streamlit Community Cloud (free, easiest)

1. Push repo to GitHub (public)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set `app.py` as entry point
4. Add `GROQ_API_KEY` in Secrets
5. Deploy — live URL in ~2 minutes

### Render / Railway

```bash
# Start command
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

Add `GROQ_API_KEY` as an environment variable in the dashboard.

> ⚠️ **Never commit your API key to Git.** Always use environment variables.

---

## 📋 Environment Variables

```env
# .env.example
GROQ_API_KEY=your_groq_api_key_here
```

---

## 🗺 Roadmap

- [ ] Anki export (.apkg format)
- [ ] Multi-deck management
- [ ] SM-2 algorithm for true spaced repetition scheduling
- [ ] Student progress persistence (SQLite / Supabase)
- [ ] Shareable deck links
- [ ] Mobile-optimised layout

---

## 🙏 Built With

- [Groq](https://groq.com) — ultra-fast LLM inference
- [Llama 3.3-70B](https://llama.meta.com) — the model doing the heavy lifting
- [Streamlit](https://streamlit.io) — rapid Python UI
- [reportlab](https://www.reportlab.com) — PDF generation

---

<div align="center">

**Built for the Cuemath AI Builder Challenge · April 2026**

*Pick a problem. Start building. Ship something you're proud of.*

</div>
