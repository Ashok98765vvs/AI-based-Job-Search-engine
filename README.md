# 🧠 USA Job Intelligence Platform

An AI-powered, resume-aware, **fresh-only** US job discovery app.
Built with **Python · Streamlit · Ollama · SQLite**, async scrapers across
**Greenhouse · Lever · Ashby · Remotive · RemoteOK · Arbeitnow · Adzuna** plus a
generic company-careers-page scraper. Everything runs locally on free APIs.

---

## ✨ Features

- 📄 **Upload resume** (PDF / DOCX / TXT) and let a local LLM extract a structured profile.
- 🤖 **Ollama-powered analysis** — target roles, related roles, seniority, tech stack, hidden ATS keywords.
- 🌐 **Parallel async scraping** of 7 free APIs + any company careers page URL.
- ⏱ **24-hour freshness** — expired jobs are auto-pruned, duplicates deduped by source/external ID.
- 🧠 **ATS engine** — Ollama scores semantic + ATS + keyword % and explains why.
- 🎯 **Ranked feed** with filters (remote, visa, salary, experience, company, stack).
- 📊 **Dashboard** with Plotly charts (jobs by source, top companies, hourly timeline, remote split).
- ⬇️ **Export** to CSV / XLSX / JSON.
- 🔌 **Optional FastAPI** for headless usage.
- 🌒 Dark UI with animated job cards, gradient score rings, soft motion.

---

## 🗂 Project structure

```
job_intel/
├── app.py                    # Streamlit entry point
├── config.py                 # Pydantic settings (.env loader)
├── requirements.txt
├── README.md
├── .env.example
│
├── ai/
│   ├── ollama_client.py      # HTTP wrapper for /api/generate
│   ├── resume_analyzer.py    # analyze_resume()
│   ├── keyword_expander.py   # generate_keywords()
│   └── ats_engine.py         # ats_score() / match_jobs()
│
├── scrapers/
│   ├── base.py
│   ├── greenhouse.py
│   ├── lever.py
│   ├── ashby.py
│   ├── remotive.py
│   ├── remoteok.py
│   ├── arbeitnow.py
│   ├── adzuna.py
│   ├── company_page.py
│   └── orchestrator.py       # fetch_all_jobs + persist_jobs
│
├── database/
│   ├── db.py                 # SQLAlchemy engine + session
│   ├── models.py             # jobs, resumes, applications, keywords, match_scores
│   └── seed.sql              # demo data
│
├── utils/
│   ├── logger.py
│   ├── cache.py              # TTL in-memory cache
│   ├── rate_limiter.py
│   ├── user_agents.py        # rotating UAs
│   ├── http.py               # async httpx + retries
│   ├── resume_parser.py      # PDF / DOCX extraction
│   ├── exporters.py          # CSV / XLSX / JSON
│   └── seed_db.py
│
├── components/               # Streamlit UI building blocks
│   ├── theme.py              # dark mode CSS + animations
│   ├── metrics.py
│   ├── filters.py
│   └── job_card.py
│
├── api/
│   └── main.py               # optional FastAPI app
│
├── data/                     # SQLite file lives here
├── exports/
├── resumes/
├── logs/
└── static/
```

---

## 🚀 Setup

### 1. Create a virtual environment

```bash
python -m venv venv
# Mac / Linux
source venv/bin/activate
# Windows
venv\Scripts\activate
```

### 2. Install Python deps

```bash
pip install -r requirements.txt
```

### 3. Install & start Ollama

Mac:    `brew install ollama`
Linux:  `curl -fsSL https://ollama.com/install.sh | sh`
Windows: download from <https://ollama.com/download>.

Start the server and pull a model:

```bash
ollama serve
ollama pull qwen2.5:3b      # recommended — small, fast, JSON-friendly
# or:  ollama pull llama3   |   ollama pull mistral
```

### 4. Configure env

```bash
cp .env.example .env
# edit values as needed (model, boards, optional Adzuna keys)
```

### 5. Run the app

```bash
streamlit run app.py
```

Streamlit opens at <http://localhost:8501>.

### 6. (Optional) Run the API

```bash
uvicorn api.main:app --reload --port 8000
# docs at http://localhost:8000/docs
```

---

## 🔑 Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Default model |
| `DATABASE_URL` | `sqlite:///data/jobintel.db` | Switch to PostgreSQL by changing URL |
| `FRESH_WINDOW_HOURS` | `24` | Job freshness window |
| `HTTP_CONCURRENCY` | `10` | Async client concurrency |
| `HTTP_RATE_PER_SEC` | `5` | Global rate limit |
| `GREENHOUSE_BOARDS` | airbnb,stripe,… | Comma-separated boards to pull |
| `LEVER_BOARDS` | netflix,palantir,… | Comma-separated boards |
| `ASHBY_BOARDS` | openai,vanta,… | Comma-separated boards |
| `ADZUNA_APP_ID/KEY` | _(empty)_ | Optional Adzuna creds |

---

## 🧠 How matching works

1. Resume text is extracted (`pdfplumber` / `python-docx`).
2. Ollama returns a JSON profile (`target_roles`, `tech_stack`, `ats_keywords`, …).
3. `keyword_expander` asks the LLM for 10–15 related US job titles.
4. Async scrapers fan out to every source, deduped by `(source, external_id)`.
5. Only jobs ≤ `FRESH_WINDOW_HOURS` old are kept; older rows are pruned each run.
6. For each job the `ats_engine` computes:
   - **ATS score** — keyword + structure compatibility
   - **Semantic score** — LLM judgment of role fit
   - **Keyword match %** — overlap of resume keywords
   - **Overall** = `0.45·ATS + 0.45·SEM + 0.10·KW`
7. Streamlit renders ranked job cards with a score ring + explanation.

---

## 🩺 Troubleshooting

| Problem | Fix |
| --- | --- |
| `Ollama not reachable` banner | Run `ollama serve` in another terminal. |
| `model not installed` | `ollama pull qwen2.5:3b` (or whatever you set in `.env`). |
| Greenhouse / Lever board returns 404 | Slug may be wrong; visit `https://boards.greenhouse.io/<slug>` to verify. |
| Adzuna returns no jobs | Set `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` in `.env`. |
| PDF text empty | The PDF may be a scanned image — OCR not included by default. |
| SQLite locked | Close other connections, or switch `DATABASE_URL` to PostgreSQL. |
| Streamlit shows stale jobs | Click **Prune expired jobs now** in the Admin tab. |

---

## 🛡 Notes

- All scrapers respect rate limits (`aiolimiter`), retry with exponential backoff (`tenacity`), and rotate user agents (`fake-useragent` with offline fallback).
- The app works fully **without Ollama** in a degraded mode: heuristic skills + keyword scoring.
- No paid APIs required — Adzuna is optional.
- For PostgreSQL, install `psycopg2-binary` and set `DATABASE_URL` accordingly.

---

## 📜 License

MIT — use freely, contributions welcome.
