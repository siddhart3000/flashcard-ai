<div align="center">

<!-- Animated Logo / Title -->
<img src="https://readme-typing-svg.demolab.com?font=Space+Grotesk&weight=700&size=42&duration=3000&pause=1000&color=38BDF8&center=true&vCenter=true&width=700&lines=⚡+Flashcard+AI;Turn+PDFs+into+Smart+Decks;Active+Recall+%2B+Spaced+Repetition;Built+for+the+Cuemath+Challenge" alt="Flashcard AI" />

<br/>

<!-- Badges Row 1 -->
[![Live Demo](https://img.shields.io/badge/🚀%20Live%20Demo-Visit%20App-38BDF8?style=for-the-badge)](https://flashcard-ai-6axech9wtfs8gabgqwzxfp.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)

<!-- Badges Row 2 -->
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036?style=for-the-badge&logo=meta&logoColor=white)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Live-00D26A?style=for-the-badge&logo=vercel&logoColor=white)](https://flashcard-ai-6axech9wtfs8gabgqwzxfp.streamlit.app/)

<br/>

> **🎯 Turn any PDF into a smart, adaptive study deck in seconds.**
> Powered by **Groq + Llama 3.3-70B**. No account needed. No credit card.

<br/>

<!-- CTA Button -->
<a href="https://flashcard-ai-6axech9wtfs8gabgqwzxfp.streamlit.app/" target="_blank">
  <img src="https://img.shields.io/badge/%E2%9A%A1%20Try%20It%20Now%20%E2%80%94%20Live%20App-flashcard--ai.streamlit.app-38BDF8?style=for-the-badge&labelColor=0f172a&color=38BDF8" height="40"/>
</a>

<br/><br/>

<!-- App Screenshot placeholder -->
<img src="https://via.placeholder.com/900x480/080c14/38bdf8?text=📸+App+Screenshot+Here+(Replace+This)" width="900" alt="Flashcard AI Demo" style="border-radius:16px; border: 1px solid #38bdf8;"/>

<br/>

</div>

---

## 🌐 Live Demo

> **🔗 [https://flashcard-ai-6axech9wtfs8gabgqwzxfp.streamlit.app/](https://flashcard-ai-6axech9wtfs8gabgqwzxfp.streamlit.app/)**

No setup. No login. Just upload a PDF and start learning.

---

## ✨ Features

<div align="center">

```
╔══════════════════════╦═══════════════════════════╗
║   🃏 Smart Cards      ║  📊 Spaced Repetition     ║
╠══════════════════════╬═══════════════════════════╣
║   ❓ MCQ Mode         ║  ⏱ Exam Mode              ║
╠══════════════════════╬═══════════════════════════╣
║   📈 Analytics        ║  📄 PDF Export            ║
╚══════════════════════╩═══════════════════════════╝
```

</div>

<table>
<tr>
<td width="50%">

### 🃏 Smart Flashcards
- PDF → deck in **seconds** via Groq API
- Cards cover definitions, relationships, edge cases & examples
- Difficulty tags: `Easy` / `Medium` / `Hard`
- Topic auto-tagging per card
- **Explain Better** — AI-powered deeper explanations on demand

</td>
<td width="50%">

### 📊 Spaced Repetition Engine
- Unknown cards appear **2× more often**
- Study modes: `Normal` · `Unknown First` · `Hard Only` · `Review Mistakes`
- Topic filter — drill one subject at a time
- Shuffle toggle
- Live **mastery %** + streak counter 🔥

</td>
</tr>
<tr>
<td>

### ❓ Multiple Choice Mode
- AI generates **3 plausible distractors** per card
- Color-coded feedback (✅ green / ❌ red)
- Cached responses — zero duplicate API calls on revisit
- Counts toward your mastery score

</td>
<td>

### ⏱ Exam Mode
- Configurable timer: **2 – 30 minutes**
- Card subsets: `All` / `Hard Only` / `Unknown Only`
- No answer previews — real exam conditions
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
- **Weak areas panel** (sorted by error rate)

</td>
<td>

### 📄 PDF Report Export
- Styled report via **reportlab** (dark theme)
- Graceful fallback to stdlib PDF if reportlab missing
- Includes: student info · summary stats · weak areas · full card list
- Generated on-demand — never slows the app

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

Open [http://localhost:8501](http://localhost:8501) in your browser. ✅ Done.

> Or skip all of this and use the **[live hosted version](https://flashcard-ai-6axech9wtfs8gabgqwzxfp.streamlit.app/)** — no setup required!

---

## 🏗 Architecture

```
flashcard-ai/
├── app.py               # Single-file Streamlit app (all logic + UI)
├── requirements.txt
├── .env.example
└── README.md
```

### Data Flow

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
      ├──► 🃏 Flashcard Tab   (flip · known/unknown · spaced repetition)
      ├──► ❓ MCQ Tab          (_cached_mcq_distractors · 4-option quiz)
      ├──► ⏱ Exam Tab         (countdown timer · no previews · result screen)
      └──► 📈 Analytics Tab   (topic breakdown · weak areas · PDF export)
```

---

## 🛠 Installation Notes

### Fix: `ModuleNotFoundError: No module named 'reportlab'`

```bash
pip install reportlab
```

If you can't install reportlab, the app **automatically falls back** to a pure-stdlib PDF generator. You still get a valid, downloadable PDF — just without the styled dark theme.

### Full dependency list

| Package | Purpose | Required? |
|---|---|---|
| `streamlit` | UI framework | ✅ Yes |
| `groq` | Llama 3.3-70B API | ✅ Yes |
| `python-dotenv` | Load `.env` file | ✅ Yes |
| `pdfplumber` | PDF text extraction (primary) | ⭐ Recommended |
| `PyMuPDF` | PDF extraction (fallback 1) | ⭐ Recommended |
| `pypdf` | PDF extraction (fallback 2) | ⭐ Recommended |
| `reportlab` | Styled PDF report | ⚠️ Optional |

---

## 🔧 Key Engineering Decisions

| Decision | Rationale |
|---|---|
| **Single `app.py`** | Easier to deploy on any platform — no import path issues |
| **`@st.cache_data` on all API calls** | Same input never hits Groq twice — instant on rerun |
| **3-attempt retry + exponential back-off** | Groq occasionally returns malformed JSON — must handle gracefully |
| **`_safe_parse_json()` strips fences** | Handles every malformed response pattern observed in production |
| **`reportlab` optional + stdlib fallback** | App never crashes from a missing dependency |
| **Deck saved as JSON** | Portable across sessions, devices, and users — no database needed |
| **Session state initialized with `if key not in`** | Never clobbers existing data on rerun |

---

## 🚢 Deployment

### ▶ Streamlit Community Cloud *(free, easiest)*

1. Push repo to GitHub (public)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set `app.py` as entry point
4. Add `GROQ_API_KEY` in **Secrets**
5. Deploy — live URL in ~2 minutes

### ▶ Render / Railway

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

- [ ] 📦 Anki export (`.apkg` format)
- [ ] 🗂 Multi-deck management
- [ ] 🧠 SM-2 algorithm for true spaced repetition scheduling
- [ ] 💾 Student progress persistence (SQLite / Supabase)
- [ ] 🔗 Shareable deck links
- [ ] 📱 Mobile-optimised layout

---

## 🙏 Built With

<div align="center">

| Tool | Role |
|---|---|
| [Groq](https://groq.com) | Ultra-fast LLM inference |
| [Llama 3.3-70B](https://llama.meta.com) | The model doing the heavy lifting |
| [Streamlit](https://streamlit.io) | Rapid Python UI |
| [reportlab](https://www.reportlab.com) | PDF generation |

</div>

---

<div align="center">

<!-- Animated footer -->
<img src="https://readme-typing-svg.demolab.com?font=Space+Grotesk&weight=600&size=18&duration=4000&pause=1000&color=94A3B8&center=true&vCenter=true&width=600&lines=Built+for+the+Cuemath+AI+Builder+Challenge+·+April+2026;Pick+a+problem.+Start+building.+Ship+something+you're+proud+of." alt="Footer" />

<br/>

**⭐ Star this repo if it helped you learn faster!**

[![GitHub stars](https://img.shields.io/github/stars/YOUR_USERNAME/flashcard-ai?style=social)](https://github.com/YOUR_USERNAME/flashcard-ai)
&nbsp;&nbsp;
[![Live Demo](https://img.shields.io/badge/🔗-Try%20Live%20Demo-38BDF8)](https://flashcard-ai-6axech9wtfs8gabgqwzxfp.streamlit.app/)

</div>
