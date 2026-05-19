# 🎙️ Meeting Live Transcribe Model - Quick Start Guide

## What Is This Project?
A real-time meeting transcription system that:
- 🎤 Captures live audio from your microphone or WebRTC
- 📝 Transcribes speech to text using Whisper + NeMo RNNT AI models
- 👤 Identifies speakers automatically (pyannote.audio)
- ✨ Cleans and formats transcripts in real-time
- 📊 Generates live meeting summaries (OpenAI)
- 🌐 Broadcasts via WebSocket to a modern web dashboard
- 🎯 All processing runs locally (privacy-first)

## System Requirements
✅ Windows 10/11 or Linux/Mac  
✅ Python 3.11+ ([Download](https://www.python.org/downloads/))  
✅ 8GB+ RAM (16GB+ recommended)  
✅ 20GB free disk space  
✅ CUDA 11.8+ (optional, for faster GPU processing)  

## Installation Steps

### 1️⃣ First Time Setup (Choose One)

#### **Option A: Automated Setup (Easiest)**
1. Open Command Prompt/PowerShell in this folder
2. Run: `setup.bat` (Windows) or follow the Python steps below
3. Wait for installation to complete

#### **Option B: Manual Python Setup**
```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate    # Windows
source venv/bin/activate # Mac/Linux

# Install all dependencies (this may take a few minutes)
pip install -r requirements.txt
```

### 2️⃣ Start the Backend

#### **Quick Start (Recommended)**
```bash
.\start_backend_simple.ps1   # Windows PowerShell
# OR
python realtime_transcriber.py
```

**Expected Output:**
```
[*] Backend starting...
[*] WebSocket listening on ws://0.0.0.0:8765
[*] Ready to receive audio...
```

#### **Advanced: Multi-Service Setup**
Open 3 separate terminals:

**Terminal 1 - NLP Service (optional):**
```bash
python nlp_service.py
# Runs on http://localhost:8100
```

**Terminal 2 - Main ASR Backend:**
```bash
python realtime_transcriber.py
# Runs on ws://localhost:8765
```

**Terminal 3 - WebRTC Ingest (for browser audio):**
```bash
python webrtc_ingest.py
# Runs on http://localhost:8081
```

### 3️⃣ (Optional) Start the Dashboard

```bash
cd frontend_dashboard
npm install              # First time only
npm run dev
```

Then open: http://localhost:3000

## Useful Commands

### Troubleshooting
```bash
# List your audio input devices
python mic_check.py

# Test ASR without frontend
python client_test.py

# Generate summary from past transcript
python meeting_summary.py --input transcripts/session_*.jsonl --prefer auto
```

### Environment Variables (Advanced)
```bash
set WHISPER_MODEL=tiny.en              # Faster but less accurate
set WHISPER_MODEL=medium.en            # Better quality
set DEVICE_ID=2                        # Select different mic (from mic_check.py)
set OPENAI_API_KEY=sk-...             # For better summaries
set PYANNOTE_TOKEN=hf_...             # For speaker identification
```

## Common Issues

### ❌ "ModuleNotFoundError: No module named X"
**Solution:** Run `pip install -r requirements.txt` again

### ❌ "No audio detected"
**Solution:** Run `python mic_check.py` to find your device ID, then set:
```bash
set DEVICE_ID=<number_from_above>
```

### ❌ "Connection refused" on port 8765
**Solution:** 
1. Check if backend is actually running
2. Verify firewall isn't blocking port 8765
3. Try: `netstat -ano | findstr 8765` to see if port is in use

### ❌ GPU not being used
**Solution:** Your PyTorch may not have CUDA support. Check:
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

## File Structure
```
├── realtime_transcriber.py    # Main backend (start this!)
├── nlp_service.py             # Text processing service
├── webrtc_ingest.py           # Browser audio receiver
├── speaker.py                 # Speaker identification
├── nlp/                       # NLP processing modules
├── frontend_dashboard/        # Next.js web UI
├── transcripts/               # Output transcriptions (auto-created)
├── debug_audio/               # Debug WAV files (auto-created)
├── requirements.txt           # Python dependencies
└── README.md                  # Full documentation
```

## Output Files
After a meeting, you'll find:
- `transcripts/session_20250501_120000.jsonl` - Live transcript with timestamps
- `transcripts/session_20250501_120000_summaries.jsonl` - Rolling summaries
- `transcripts/session_20250501_120000_final_summary.md` - Final summary

## Architecture Overview
```
🎤 Audio Input
    ↓
🔊 Audio Capture (sounddevice / WebRTC)
    ↓
📊 Voice Activity Detection (VAD)
    ↓
🧠 ASR Engine (NeMo RNNT + Whisper)
    ↓
✨ NLP Pipeline (Cleaning, Formatting)
    ↓
👤 Speaker ID (pyannote.audio)
    ↓
📝 Summarization (OpenAI GPT)
    ↓
🌐 WebSocket Broadcast
    ↓
📱 Dashboard / External Apps
```

## Next Steps
1. ✅ Install dependencies
2. ✅ Start `realtime_transcriber.py`
3. 🎙️ Speak into your microphone
4. 📊 See live transcripts appear
5. (Optional) Open frontend dashboard at http://localhost:3000

## Support
- 📖 See `README.md` for full documentation
- 🏗️ See `ARCHITECTURE.md` for technical details
- 🐛 Check console output for error messages

## Key Ports
- `8765` - WebSocket (Backend ↔ Frontend)
- `8100` - NLP Service HTTP
- `8081` - WebRTC Ingest
- `3000` - Frontend Dashboard

---

**Happy transcribing! 🎙️✨**
