# Deploy: Vercel (frontend) + Railway (backend)

## Architecture

| Service | Platform | URL |
|---------|----------|-----|
| Next.js UI | **Vercel** | `https://your-app.vercel.app` |
| ASR WebSocket + NLP | **Railway** | `wss://your-backend.up.railway.app` |

Live transcription uses **WebSocket audio** from the browser to Railway (same connection as Connect). WebRTC ingest on port 8081 is optional and usually **not** needed on Railway unless you add a second Railway service.

---

## 1. Push code to GitHub

```bash
cd Meeting-Live-Transcribe-Model-main
git init
git add .
git commit -m "Prepare Vercel + Railway deploy"
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

---

## 2. Railway (backend)

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**.
2. Select this repository (root folder, not `frontend_dashboard`).
3. Railway reads `railway.toml` and builds `Dockerfile.railway`.
4. **Settings → Variables** — copy from `.env.railway.example`:

   | Variable | Value |
   |----------|--------|
   | `USE_LOCAL_MIC` | `False` |
   | `SPEAKER_ID_ENABLED` | `False` |
   | `WHISPER_MODEL` | `base.en` |
   | `WHISPER_LANGUAGE` | `en` |
   | `CHUNK_DURATION` | `2.5` |

5. **Settings → Networking → Generate domain** (e.g. `meeting-asr-production.up.railway.app`).
6. Wait until deploy is **Active** (first build downloads Whisper; can take 5–15 min).
7. **Recommended plan:** at least **2 GB RAM** (Whisper `base.en` on CPU).

**WebSocket URL for frontend:**

```
wss://YOUR-RAILWAY-DOMAIN.up.railway.app
```

(Test: browser console → `new WebSocket("wss://YOUR-DOMAIN.up.railway.app")` should connect.)

---

## 3. Vercel (frontend)

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → import the **same GitHub repo**.
2. **Root Directory:** `frontend_dashboard` (important).
3. Framework: **Next.js** (auto-detected).
4. **Environment Variables:**

   | Name | Value |
   |------|--------|
   | `NEXT_PUBLIC_WS_URL` | `wss://YOUR-RAILWAY-DOMAIN.up.railway.app` |
   | `NEXT_PUBLIC_SIGNAL_URL` | `https://YOUR-RAILWAY-DOMAIN.up.railway.app/offer` *(optional; WS audio works without WebRTC)* |

5. **Deploy**.

6. Open `https://your-app.vercel.app` → **Connect** → speak (allow mic).

---

## 4. Checklist after deploy

- [ ] Railway logs show: `WebSocket server listening on ws://0.0.0.0:...`
- [ ] Vercel app shows **Connected** (green) after Connect
- [ ] Sidebar shows **Audio: WebSocket OK**
- [ ] Speak 3+ seconds; transcript appears in ~3–5 s

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Connect fails on Vercel | Use `wss://` not `ws://`; Railway domain must be HTTPS/WSS |
| Railway build OOM | Upgrade RAM or set `WHISPER_MODEL=tiny.en` |
| No transcript | Check Railway logs for `ASR chunk` / `Whisper raw`; speak louder |
| CORS / mic blocked | Site must be HTTPS (Vercel); allow microphone in browser |

---

## Optional: WebRTC on Railway (advanced)

Run a **second** Railway service from the same repo with start command:

```bash
python webrtc_ingest.py
```

Set `ASR_WS_URL=ws://YOUR-FIRST-SERVICE.internal:PORT` or public `wss://` URL. Point Vercel `NEXT_PUBLIC_SIGNAL_URL` to the second service `/offer` URL.

For most demos, **WebSocket-only audio is enough**.
