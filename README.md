# MeetScribe AI — Live Meeting Transcription & Summarization

> **AI-powered real-time meeting assistant** — microphone se awaaz capture karke turant text (transcript) banata hai, speakers alag dikhata hai, aur meeting ka short summary bhi deta hai.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-Frontend-000000?logo=next.js&logoColor=white)
![Whisper](https://img.shields.io/badge/ASR-Whisper-412991)
![AI](https://img.shields.io/badge/AI-NLP%20%2B%20Summary-22c55e)

[![CI](https://github.com/ashish8513/ai-meeting-live-transcriber/actions/workflows/ci.yml/badge.svg)](https://github.com/ashish8513/ai-meeting-live-transcriber/actions/workflows/ci.yml)

---

## Table of contents

- [Project kya hai? (Overview)](#project-kya-hai-overview)
- [Auth + Admin Panel (JWT + PostgreSQL)](#auth--admin-panel-jwt--postgresql)
- [Code explore karo](#code-explore-karo)
- [Main features](#main-features)
- [Tech stack](#tech-stack)
- [System architecture](#system-architecture)
- [Project structure](#project-structure)
- [Installation & run (local)](#installation--run-local)
- [Environment variables](#environment-variables)
- [WebSocket messages](#websocket-messages)
- [Deploy online](#deploy-online)
- [GitHub par push kaise karein](#github-par-push-kaise-karein)
- [Suggested repository names](#suggested-repository-names)
- [License & credits](#license--credits)

---

## Project kya hai? (Overview)

**MeetScribe AI** ek full-stack project hai jo **online meetings / classes / discussions** ke liye banaya gaya hai:

| Step | Kya hota hai |
|------|----------------|
| 1 | User browser se **mic allow** karta hai aur **Connect** dabata hai |
| 2 | Audio backend ko jata hai (WebSocket / WebRTC) |
| 3 | **Whisper (Faster-Whisper)** speech ko text mein convert karta hai — **live captions** |
| 4 | **NLP pipeline** fillers, repeat words, hallucinations clean karti hai |
| 5 | Optional: **Speaker ID** — Speaker 1, 2, 3… |
| 6 | **AI summary** — har **5 sec** rolling summary (DB + admin panel) |
| 7 | Optional: **Translation** — subtitles alag language mein |
| 8 | Session **`transcripts/`** folder mein save ho sakta hai |

**Use cases:** college project demo, online class notes, team meeting minutes, accessibility (hearing support), research on ASR + NLP.

---

## Auth + Admin Panel (JWT + PostgreSQL)

| Feature | Details |
|---------|---------|
| **Register / Login** | FastAPI + JWT (`/api/auth/register`, `/api/auth/login`) |
| **Database** | PostgreSQL — users, meeting sessions, rolling summaries |
| **Admin dashboard** | `http://localhost:3000/admin` — har **5 sec** naye summaries (auto-refresh) |
| **Summary ingest** | ASR backend → `POST /api/internal/summaries` (har 5 sec) |

### URLs (local)

| Page | URL |
|------|-----|
| Meeting UI | http://localhost:3000 |
| Login | http://localhost:3000/login |
| Register | http://localhost:3000/register |
| **Admin panel** | http://localhost:3000/admin |
| Auth API docs | http://localhost:8200/docs |

**Pehla registered user automatically `admin` ban jata hai** (ya `.env` mein `ADMIN_EMAIL` set karo).

### Quick start (auth stack)

```powershell
# 1. PostgreSQL
docker compose up -d postgres

# 2. Dependencies
pip install -r requirements.txt -r requirements-auth.txt

# 3. .env
copy .env.example .env
# JWT_SECRET, DATABASE_URL, INTERNAL_API_KEY set karo

# 4. Full stack
.\run_stack.ps1
```

### Auth API endpoints

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/auth/register` | Public |
| POST | `/api/auth/login` | Public |
| GET | `/api/auth/me` | JWT Bearer |
| GET | `/api/admin/dashboard` | Admin JWT |
| GET | `/api/admin/summaries` | Admin JWT |
| POST | `/api/internal/summaries` | `X-Internal-Key` header |

---

## Code explore karo

1. **Pehle UI dekho** — `frontend_dashboard/pages/index.js` (Connect, transcript list, summaries).
2. **Backend flow** — `realtime_transcriber.py` (audio → Whisper → WebSocket broadcast).
3. **NLP samjho** — `nlp/pipeline.py` aur `nlp/README.md`.
4. **Microservice** — `nlp_service.py` (FastAPI, port 8100).
5. **WebRTC** — `webrtc_ingest.py` (browser audio ingest).
6. **Auth API** — `api/main.py`, `api/routers/auth.py`, `api/models.py`
7. **Admin UI** — `frontend_dashboard/pages/admin/index.js`
8. **Experiments:** `WHISPER_MODEL=tiny.en` vs `base.en`, `SUMMARY_INTERVAL=5`

Detailed day-by-day work: **[CHANGELOG.md](./CHANGELOG.md)**

---

## Main features

- Live audio capture (mic / browser WebRTC)
- **Voice Activity Detection (VAD)** — sirf bolne par process
- **Faster-Whisper** transcription (`base.en` default, env se change)
- **Interim + final** captions — kam lag, zyada real-time feel
- **Speaker identification** (optional, pyannote embeddings)
- **NLP post-processing** — noise, fillers, duplicates, hallucination blocklist
- **JWT login/register** + PostgreSQL user store
- **Admin panel** — live summaries har 5 sec (DB + UI refresh)
- **Rolling + full meeting summaries** (OpenAI GPT ya rule-based; default **5 sec**)
- **Multi-language subtitles** (MarianMT translation)
- **Next.js dashboard** — Zoom-style meeting UI
- **Session export** — JSONL transcripts + summaries
- **Docker + Railway + Vercel** deploy support

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js, React, WebSocket, WebRTC |
| Auth API | FastAPI, JWT (python-jose), SQLAlchemy |
| Database | PostgreSQL 16 |
| ASR backend | Python 3.11, Faster-Whisper, WebSockets |
| NLP | Custom pipeline + FastAPI (`nlp_service.py`) |
| Speaker ID | pyannote.audio (optional) |
| Summaries | OpenAI API / Hugging Face Transformers |
| Translation | MarianMT |
| CI | GitHub Actions |
| Deploy | Railway (backend), Vercel (frontend) |

---

## System architecture

```mermaid
flowchart LR
  subgraph Browser
    UI[Meeting UI :3000]
    ADM[Admin Panel /admin]
  end
  subgraph Backend
    AUTH[Auth API :8200]
    PG[(PostgreSQL)]
    WS[realtime_transcriber :8765]
    WH[Whisper ASR]
    NLP[nlp_service :8100]
  end
  UI -->|JWT login| AUTH
  ADM -->|JWT admin| AUTH
  AUTH --> PG
  UI -->|audio WS| WS
  WS --> WH
  WS --> NLP
  WS -->|summary every 5s| AUTH
  AUTH --> PG
  ADM -->|poll 5s| AUTH
```

**Ek command se sab start (Windows):**

```powershell
.\run_stack.ps1
```

Ye 4 cheezein kholti hai: NLP service → ASR backend → WebRTC ingest → frontend (`http://localhost:3000`).

---

## Project structure

```
.
├── api/                      # FastAPI auth + admin + PostgreSQL
│   ├── main.py
│   ├── models.py
│   └── routers/
├── docker-compose.yml        # Postgres + Auth API + Frontend (+ stack profile)
├── Dockerfile.auth           # Auth API image
├── Dockerfile.nlp            # NLP microservice
├── realtime_transcriber.py   # Main ASR + WebSocket server (core)
├── nlp_service.py            # FastAPI NLP microservice
├── webrtc_ingest.py          # Browser audio ingest (WebRTC)
├── speaker.py                # Speaker embedding / labeling
├── cleaner.py                # Text cleanup helpers
├── repeat_remove.py          # Overlap / duplicate removal
├── finalizer.py              # Sentence finalization
├── nlp/                      # Streaming NLP pipeline
│   ├── pipeline.py
│   ├── filters/
│   └── config/rules.json
├── frontend_dashboard/       # Next.js UI
│   ├── pages/index.js        # Live meeting
│   ├── pages/login.js
│   ├── pages/register.js
│   └── pages/admin/index.js  # Admin dashboard
├── transcripts/              # Saved sessions (gitignored)
├── run_stack.ps1             # Start full stack (Windows)
├── start_backend_simple.ps1  # Backend only
├── requirements.txt
├── Dockerfile.railway        # Cloud deploy
├── DEPLOY.md                 # Vercel + Railway guide
└── .github/workflows/ci.yml  # Automated build checks
```

---

## Installation & run (local)

### Requirements

- **Python 3.11** (recommended)
- **Node.js 20+** (frontend)
- **Windows 10/11** (scripts `.ps1`); Mac/Linux par commands manually chala sakte ho
- Optional: **CUDA GPU** for faster Whisper
- Optional: **OpenAI API key** for GPT summaries
- Optional: **Hugging Face token** (`PYANNOTE_TOKEN`) for speaker ID

### Step 1 — Python backend

```powershell
cd path\to\project
copy .env.example .env
# .env mein apni OPENAI_API_KEY / PYANNOTE_TOKEN likho (ye file Git par push nahi hoti)
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt -r requirements-auth.txt
docker compose up -d postgres
```

### Step 2 — Frontend

```powershell
cd frontend_dashboard
npm install
```

### Step 3 — Run everything

```powershell
cd ..
.\run_stack.ps1
```

Browser mein kholo: **http://localhost:3000** → **Connect** → mic allow → bolna shuru karo.

### Backend only (without UI)

```powershell
.\venv\Scripts\activate
$env:USE_LOCAL_MIC = "True"   # system mic use karne ke liye
python realtime_transcriber.py
```

WebSocket: `ws://localhost:8765`

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `base.en` | Whisper size: `tiny.en`, `base.en`, `small.en`, … |
| `WHISPER_LANGUAGE` | `en` | Language code |
| `WEBSOCKET_HOST` | `0.0.0.0` | Bind address |
| `WEBSOCKET_PORT` | `8765` | WebSocket port |
| `USE_LOCAL_MIC` | `False` | `True` = PC mic; `False` = browser audio path |
| `OPENAI_API_KEY` | — | GPT rolling / full summaries |
| `PYANNOTE_TOKEN` | — | Hugging Face token for speaker embeddings |
| `NLP_SERVICE_URL` | `http://localhost:8100` | NLP microservice URL |
| `DEVICE_ID` | `1` | sounddevice input index |
| `CHUNK_DURATION` | `2.5`–`3.0` | ASR chunk length (seconds) |
| `SUMMARY_INTERVAL` | `5` | Rolling summary interval (sec) → admin panel |
| `AUTH_API_URL` | `http://localhost:8200` | Auth API for DB ingest |
| `INTERNAL_API_KEY` | — | Key for `/api/internal/summaries` |
| `DATABASE_URL` | `postgresql+psycopg2://meetscribe:meetscribe@localhost:5432/meetscribe` | PostgreSQL |
| `JWT_SECRET` | — | JWT signing secret (change in production) |
| `ADMIN_EMAIL` | — | Optional: is email ko admin role |

Copy Railway example: `.env.railway.example`  
Copy Vercel example: `frontend_dashboard/.env.vercel.example`

---

## WebSocket messages

Backend frontend ko JSON bhejta hai:

**Final transcript:**
```json
{
  "type": "transcript",
  "timestamp": "12:00:05",
  "speaker": "SPEAKER_1",
  "text": "Hello everyone, welcome to the meeting."
}
```

**Interim (live typing effect):**
```json
{
  "type": "interim",
  "speaker": "SPEAKER_1",
  "text": "Hello every..."
}
```

**Summary:**
```json
{
  "type": "summary",
  "timestamp": "12:01:10",
  "text": "Team discussed project deadline and tasks."
}
```

Saved files (local run):

- `transcripts/session_YYYYMMDD_HHMMSS.jsonl`
- `transcripts/session_YYYYMMDD_HHMMSS_summaries.jsonl`

---

## Deploy online

Production deploy (free tier friendly):

- **Frontend** → [Vercel](https://vercel.com) (`frontend_dashboard` folder)
- **Backend** → [Railway](https://railway.app) (root + `Dockerfile.railway`)

Full steps: **[DEPLOY.md](./DEPLOY.md)**

---

## GitHub par push kaise karein

### 1. GitHub par naya repository banao

- GitHub → **New repository**
- Name: recommended **`ai-meeting-live-transcriber`** (neeche aur options)
- Public ya Private choose karo
- **README mat add karo** (repo empty rakho — local README push hogi)

### 2. Local project se push

```powershell
cd "d:\Meeting-Live-Transcribe-Model-main\Meeting-Live-Transcribe-Model-main"

git init
git add .
git commit -m "Initial commit: MeetScribe AI live meeting transcription"
git branch -M main
git remote add origin https://github.com/ashish8513/ai-meeting-live-transcriber.git
git push -u origin main
```

> **Note:** `venv/`, `node_modules/`, `.next/`, `transcripts/` already `.gitignore` mein hain — ye push nahi honge.

---

## Suggested repository names

GitHub par **short, professional, searchable** naam best rehte hain:

| Priority | Repository name | Kyon achha hai |
|----------|-----------------|----------------|
| ⭐ **Recommended** | `ai-meeting-live-transcriber` | Clear, SEO-friendly, project type samajh aa jata hai |
| 2 | `meetscribe-ai` | Brand-style, short, memorable |
| 3 | `smart-meeting-assistant-ai` | Academic / portfolio friendly |
| 4 | `live-class-transcription-ai` | College / classroom focus |
| 5 | `whisper-meeting-nlp-stack` | Technical audience ke liye |

**Display title (README heading):** MeetScribe AI  
**Repo URL example:** `github.com/yourname/ai-meeting-live-transcriber`

---

## Post-meeting summary (optional script)

Agar `meeting_summary.py` available ho:

```powershell
python meeting_summary.py --input transcripts/session_....jsonl --prefer auto
```

Output: `*_final_summary.md` transcript ke saath.

---

## Docker

**Core stack** (PostgreSQL + Auth API + Frontend):

```bash
copy .env.docker.example .env
docker compose up -d --build
```

- UI: http://localhost:3000  
- Auth API docs: http://localhost:8200/docs  
- Admin: `admin@meetscribe.com` / `Admin@123`

**Full stack** (+ NLP + ASR WebSocket/WebRTC):

```bash
docker compose --profile stack up -d --build
```

**GPU ASR only** (server with NVIDIA):

```bash
docker build -f Dockerfile -t meetscribe-asr-gpu .
docker run --gpus all -p 8765:8765 -p 8081:8081 \
  -e OPENAI_API_KEY=your_key \
  -e AUTH_API_URL=http://host.docker.internal:8200 \
  meetscribe-asr-gpu
```

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Postgres, auth-api, frontend (+ optional `stack` profile) |
| `Dockerfile.auth` | JWT Auth API (port 8200) |
| `Dockerfile.nlp` | NLP service (port 8100) |
| `Dockerfile.railway` | CPU ASR for Railway / compose `stack` |
| `frontend_dashboard/Dockerfile` | Next.js UI (port 3000) |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Kuch print nahi ho raha | `run_stack.ps1` se start karo; mic allow check karo |
| WebSocket error | Backend `8765` par chal raha hai? Firewall check |
| Slow / high CPU | `WHISPER_MODEL=tiny.en` set karo |
| "Thank you" galat text | NLP blocklist on; `RECORD_DEBUG_AUDIO=False` |
| Zoom/Meet system audio | Loopback device (VB-CABLE) ya browser WebRTC path use karo |

---

## License & credits

- **Whisper** — OpenAI  
- **Faster-Whisper**, **pyannote**, **Transformers** — open-source community  
- Built as an **AI + NLP + Full-Stack** learning & demo project  

---

**Viva / demo prep:** [Overview](#project-kya-hai-overview) → [Architecture](#system-architecture) → [Project structure](#project-structure) → [CHANGELOG.md](./CHANGELOG.md).
