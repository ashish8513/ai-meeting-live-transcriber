# Development Changelog

Project progress log (for reviewers and viva/demo context).

## November 2025

### 09/11/2025
- Created UI for real-time transcription and summaries
- Connected backend and frontend
- Enhanced older code to support more features
- Added OpenAI summarization model
- Added feature to save transcript and summaries to files
- Transcript AI filters unnecessary / non-speech audio

### 11/11/2025
- Fixed word flickering on the frontend
- Improved speaker recognition: backend analyzes speech, assigns Speaker 1 / 2 / 3 on the web page

### 12/11/2025
- Reduced perceived delay: interim + final results sent to frontend while backend still analyzes

### 13/11/2025
- Docker setup for backend, NLP, and client test
- WebSocket API: `ws://<host>:8765`

### 17/11/2025
- Full codebase review (`realtime_transcriber.py` vs helpers)
- Fixed microphone stream not starting (empty audio queue)
- RNNoise + `WHISPER_MODEL` env alignment

### 18/11/2025
- Mic allow/select from web page
- VAD/RMS tuning; WebSocket + Next.js connection fixes
- End-to-end validation with `client_test.py` and dashboard

### 19/11/2025
- Latency research: Whisper + NeMo RNNT pipeline
- `run_stack.ps1`, WebRTC ingest, NLP service wiring
- WebRTC int16→float scaling fix

### 20/11/2025
- Whisper hallucination debug ("Thank you" issue)
- WebRTC stereo→mono and normalization fixes
- `medium.en` + float32 for better accent recognition
- `debug_audio/` for QA

### 21/11/2025
- Ingest speed-up and chunk overlap tuning
- Hard dedupe for overlapping chunks
- Pre-ASR diagnostics and WAV dumps

### 22/11/2025
- NLP modules: `cleaner`, `repeat_remove`, `finalizer`
- Hallucination blocklist and silence finalization

### 24/11/2025
- Whisper `tiny.en` for lower latency
- Rolling 5-minute summaries + full-session summary (OpenAI)
- Frontend summary sidebar and full-summary view

### 25/11/2025
- GitHub Actions CI (Python + Next.js build)
- NLP pipeline and audio pre-processing improvements

### 26/11/2025
- Advanced NLP post-processing
- Speaker diarization and friendly speaker labels

### 27/11/2025
- MarianMT translation + subtitle language selector
- ASR → NLP → caption flow end-to-end
