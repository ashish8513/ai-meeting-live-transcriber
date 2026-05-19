# 🎙️ Project Chala De - Your Real-Time Meeting Transcriber is Ready!

## TL;DR (बस चला दो! 🚀)

### Option 1: Super Fast (Easiest)
```
python realtime_transcriber.py
```
That's it! Backend starts on `ws://localhost:8765`

### Option 2: Full Setup with UI
```bash
# Terminal 1: Backend
python realtime_transcriber.py

# Terminal 2: Frontend (optional but cool)
cd frontend_dashboard
npm run dev
# Then open http://localhost:3000
```

---

## 📋 Initial Setup (One-Time Only)

### Step 1: Check Python
```bash
python --version
```
Need **Python 3.11+**? Get it from https://www.python.org

### Step 2: Install Dependencies
```bash
# Create isolated environment
python -m venv venv

# Activate it
venv\Scripts\activate    # Windows
source venv/bin/activate # Mac/Linux

# Install all requirements
pip install -r requirements.txt
```

### Step 3: Run!
```bash
python realtime_transcriber.py
```

---

## 🎯 What Happens When You Run It

The backend will:
1. ✅ Load AI models (Whisper + NeMo RNNT)
2. ✅ Start listening on WebSocket `ws://0.0.0.0:8765`
3. ✅ Wait for audio from your mic or WebRTC
4. ✅ Transcribe in real-time
5. ✅ Identify speakers automatically
6. ✅ Generate live summaries
7. ✅ Save everything to `transcripts/` folder

---

## 🛠️ Helpful Commands

### Test Your Setup
```bash
# List your microphones
python mic_check.py

# Test WebSocket connection
python client_test.py

# Run specific model/device
set WHISPER_MODEL=tiny.en     # Faster
set DEVICE_ID=2               # Different mic
python realtime_transcriber.py
```

### Generate Meeting Summary
```bash
python meeting_summary.py --input transcripts/session_*.jsonl --prefer auto
```

---

## 📊 What Gets Saved

After running a meeting, check `transcripts/`:
```
session_20250501_120000.jsonl           ← Raw transcript with timestamps
session_20250501_120000_summaries.jsonl ← Rolling summaries  
session_20250501_120000_final_summary.md ← Final report
debug_audio/                            ← Raw audio files (if enabled)
```

---

## 🌐 Frontend Dashboard (Optional)

Want a fancy web UI? 

```bash
cd frontend_dashboard
npm install
npm run dev
```

Then open: **http://localhost:3000**

You'll see:
- 📝 Live transcript with speaker labels
- 📊 Real-time summaries
- 🎤 Microphone selector
- 📥 Audio stream status

---

## 🚨 Troubleshooting

### ❌ "No module named X"
```bash
pip install -r requirements.txt
```

### ❌ "Audio not detected"
1. Run: `python mic_check.py`
2. Find your device number
3. Set: `set DEVICE_ID=<number>`

### ❌ "Cannot connect to localhost:8765"
```bash
# Check if port is free
netstat -ano | findstr 8765

# Make sure backend is running in another terminal
python realtime_transcriber.py
```

### ❌ "CUDA not available" (GPU)
It's ok! Will use CPU (slower but works). To enable GPU:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## ⚙️ Advanced Configuration

Create `.env` file in project root:
```
# Model
WHISPER_MODEL=small.en
WHISPER_LANGUAGE=en

# Audio input
DEVICE_ID=1
USE_LOCAL_MIC=False

# Features
SPEAKER_ID_ENABLED=True
RECORD_DEBUG_AUDIO=False

# APIs
OPENAI_API_KEY=sk-...
PYANNOTE_TOKEN=hf_...

# Server
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8765
```

---

## 📁 Project Structure

```
.
├── realtime_transcriber.py     ← Start this! Main backend
├── nlp_service.py              ← Optional: Text cleaning service
├── webrtc_ingest.py            ← Optional: Browser audio receiver
├── speaker.py                  ← Speaker ID logic
├── nlp/                        ← Text processing modules
├── frontend_dashboard/         ← Next.js web UI
├── transcripts/                ← Your saved meetings (auto-created)
├── debug_audio/                ← Debug files (auto-created)
└── requirements.txt            ← Python dependencies
```

---

## 🎯 Workflow Examples

### Example 1: Record from Mic
```bash
python realtime_transcriber.py
# Speak into your mic
# Press Ctrl+C to stop
# Check: transcripts/session_*.jsonl
```

### Example 2: With Web Dashboard
```bash
# Terminal 1
python realtime_transcriber.py

# Terminal 2
cd frontend_dashboard && npm run dev
# Open http://localhost:3000
```

### Example 3: WebRTC (Browser Audio)
```bash
set USE_LOCAL_MIC=False
python realtime_transcriber.py
python webrtc_ingest.py
# Use WebRTC endpoint in browser
```

---

## 📞 Default Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| ASR Backend | `ws://0.0.0.0:8765` | Main speech recognition WebSocket |
| NLP Service | `http://0.0.0.0:8100` | Text processing API |
| WebRTC Ingest | `http://0.0.0.0:8081` | Browser audio receiver |
| Frontend | `http://localhost:3000` | Web dashboard |

---

## 💡 Tips

- Use **tiny.en** model for ultra-low latency (trade-off: accuracy)
- Use **medium.en** for best quality (requires more GPU/CPU)
- Enable `RECORD_DEBUG_AUDIO=True` to debug audio issues
- Check `debug_audio/` folder to hear processed audio
- Frontend is optional - backend works standalone

---

## 🆘 Still Stuck?

1. Check `QUICK_START.md` for more details
2. Read `README.md` for full documentation
3. Review `ARCHITECTURE.md` for technical deep-dive
4. Run `python mic_check.py` to verify audio setup

---

## ✨ Ready?

```bash
python realtime_transcriber.py
```

**Go forth and transcribe! 🚀**
