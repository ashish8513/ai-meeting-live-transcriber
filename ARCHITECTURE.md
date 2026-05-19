# Meeting Live – Full Architecture (Backend + Frontend)

This document explains the complete architecture of the **Meeting Live** project:

- Real‑time transcription pipeline (audio → ASR → NLP cleanup → UI)
- Speaker diarization and speaker naming
- Rolling and final summaries
- Frontend Next.js dashboard
- Supporting tools and offline utilities

All file paths below are relative to the project root `ai/`.

---

## 1. High‑Level System Overview

**Goal:** Capture live audio from online meetings, transcribe it in real time, clean the text, identify speakers, and generate rolling + final summaries, with a Zoom‑style UI.

### Main Runtime Components

- **Frontend UI**
  - `frontend_dashboard/` (Next.js 14, React 18)
  - Shows live transcript, rolling summaries, full summary, speakers list, and a Zoom‑style layout.

- **WebRTC Ingest Service**
  - `webrtc_ingest.py` (aiohttp + aiortc)
  - Accepts WebRTC SDP offers from the browser, receives audio RTP, converts to 16 kHz float frames, and pushes them over WebSocket to the ASR backend.

- **ASR Backend (Real‑Time)**
  - `realtime_transcriber.py`
  - WebSocket server on `ws://0.0.0.0:8765`
  - Core pipeline: audio queue → VAD / normalization / denoising → Whisper (and optional RNNT) → NLP cleanup → interim/final text → summaries.

- **NLP Microservice (optional / currently commented)**
  - `nlp_service.py`
  - Would provide `/correct` endpoint for deeper NLP post‑processing, but code is currently commented out.

- **Offline Tools**
  - `meeting_summary.py` – Generate a final markdown summary from saved transcripts.
  - `asr_api.py` – FastAPI ASR service for non‑real‑time file transcription.
  - `secure_speaker_test.py`, `test_speaker*.py`, `test_nlp_pipeline.py` – local tests and diagnostics.

### High‑Level Data Flow

```text
+--------------------------+          +-------------------------------+
|  Browser (Next.js UI)   |          |  Backend Machine (Python)     |
| - Mic/WebRTC audio      |          |                               |
| - WebSocket to ASR      |          |   +-----------------------+   |
+------------+-------------+   offer |   |  webrtc_ingest.py     |   |
             | WebRTC SDP /---------+--->| - HTTP POST /offer    |   |
             | answer        audio RTP   | - aiortc PeerConnection|  |
             |                          | - resample+speedup     |   |
             | WS JSON: interim,        | - WS → ASR backend     |   |
             | transcript, summary      +-----------+-----------+   |
             |                                      |               |
             |                        ws://localhost:8765 (float32) |
             |                                      v               |
             |                       +--------------+------------+  |
             |                       | realtime_transcriber.py  |  |
             |                       | - VAD, RNNoise, normalize|  |
             |                       | - Whisper / RNNT ASR     |  |
             |                       | - NLP pipeline           |  |
             |                       | - Speaker ID             |  |
             |                       | - Summaries (OpenAI)     |  |
             |                       +--------------+-----------+  |
             |                                      |              |
             |                      ws JSON: interim/summary       |
             +--------------------------------------+---------------+
                                                    |
                                                    v
                                     transcripts/session_*.jsonl
                                     transcripts/session_*_summaries.jsonl
```

---

## 2. How Services Are Started (run_backend.ps1 & Docker)

### `run_backend.ps1`

This PowerShell script wires the full stack on Windows:

- Activates the virtual environment.
- Sets environment variables:
  - **NLP / OpenAI**: `OPENAI_API_KEY`, `openai_api_key`, `NLP_LM_MODEL`, `NLP_SERVICE_URL`.
  - **Speaker ID**: `PYANNOTE_TOKEN`.
  - **ASR / RNNT**: `USE_LOCAL_MIC`, `RNNT_ONNX_ENCODER`, `RNNT_ONNX_DECODER`, `RNNT_MAX_SYMBOLS_PER_STEP`, thread env vars.
  - **Audio debug**: `USE_RNNOISE`, `RECORD_DEBUG_AUDIO`, optional `WHISPER_SPEEDUP_FACTOR`, VAD/RMS tuning (commented templates).
  - **WebRTC ingest → ASR backend**: `ASR_WS_URL="ws://localhost:8765"`.
- Starts processes:
  - `python realtime_transcriber.py` – RNNT/Whisper ASR backend (WebSocket).
  - `python webrtc_ingest.py` – WebRTC ingest HTTP server on `0.0.0.0:8081`.
  - Optionally (commented): `python nlp_service.py`, `npm run dev` in `frontend_dashboard`.

### Dockerfile

- Based on `nvidia/cuda:12.2.0-cudnn8-runtime-ubuntu22.04` with Python 3 + audio libs.
- Installs Python dependencies from `requirements.txt`.
- Copies entire repo into `/app`.
- Exposes port `8765` and runs `python3 realtime_transcriber.py` by default.

**Note:** Docker image only runs the ASR WebSocket backend. WebRTC ingest + frontend should be run separately or added to the container if needed.

---

## 3. Real‑Time ASR Pipeline (WebRTC Path)

### 3.1 Ingest: `webrtc_ingest.py`

**Role:** Bridge between browser WebRTC audio and ASR WebSocket backend.

Key parts:

- Environment:
  - `ASR_WS_URL` (default `ws://localhost:8765`) – where to send 20 ms audio frames.
- HTTP server (aiohttp):
  - Route `POST /offer` → `offer()`.
  - Uses `RTCPeerConnection` (aiortc) to handle WebRTC SDP offer/answer.
- `offer()` flow:
  - Parse JSON body with `sdp`, `type`, `session_id/stream_id`.
  - Create `RTCPeerConnection`, register `on_track` callback.

```python
@pc.on("track")
async def on_track(track):
    if track.kind != "audio": return
    async with websockets.connect(ASR_WS_URL) as ws:
        await ws.send(config JSON with stream_id + language)
        while True:
            frame = await track.recv()
            pcm = frame.to_ndarray()         # possibly stereo
            mono = pcm.mean(axis=0) or pcm   # to mono float32
            normalize to [-1,1]
            apply INGEST_SPEEDUP_FACTOR
            resample → 16 kHz float32
            accumulate into buffer
            send 20 ms frames as raw float32 bytes to ASR WS
```

- `INGEST_SPEEDUP_FACTOR` (default `2.0`) speeds up ingest to reduce latency while keeping pitch preserved downstream.

### 3.2 ASR Backend: `realtime_transcriber.py`

**Role:** Core real‑time transcription and summarization engine.

#### 3.2.1 Model and Config Initialization

Imports and models:

- **Audio / IO:** `sounddevice`, `numpy`, `webrtcvad`, `queue`, `threading`, `wave`.
- **ASR models:**
  - `WhisperModel` from `faster_whisper` – primary streaming ASR.
  - NeMo RNNT: `ASRModel` + `ONNXGreedyBatchedRNNTInfer` – alt ASR using ONNX encoder/decoder.
- **NLP:** `nlp.pipeline.process_interim_text`, `nlp.formatting.format_segment`.
- **Speaker ID:** `speaker.get_speaker_model` → `SpeakerModel` (pyannote embeddings).
- **Summarization + LM correction:** OpenAI (`SUMMARY_MODEL`, `LM_CORRECTION_MODEL`), optional `NLP_SERVICE_URL`.

Key configuration constants:

- Sample rate, chunking:
  - `SAMPLE_RATE = 16000`
  - `CHUNK_DURATION`, `OVERLAP_DURATION`, `CHUNK_SIZE`, `CHUNK_ADVANCE`
- WebSocket server:
  - `WEBSOCKET_HOST`, `WEBSOCKET_PORT = 8765`
- VAD and gating:
  - `VAD_AGGRESSIVENESS`, `VAD_MIN_VOICED_RATIO`, `RMS_MIN_LEVEL`, `NO_SPEECH_THRESHOLD`.
- Interim behavior:
  - `INTERIM_ENABLED`, `INTERIM_MIN_INTERVAL`, `INTERIM_SIMILARITY_SKIP`, `INTERIM_USE_STABLE_PREFIX`, `INTERIM_PREFIX_DEPTH`, `INTERIM_REQUIRE_WORD_BOUNDARY`, `INTERIM_MIN_CHARS_DELTA`.
- Finalization:
  - `STABLE_SIMILARITY_FINAL`, `STABLE_ROUNDS_REQUIRED`, `MIN_ALPHA_FINAL`, `SILENCE_FINALIZE_SEC`, `DEBOUNCE_SECONDS`.
- Speaker ID:
  - `SPEAKER_THRESHOLD`, `SPEAKER_ID_ENABLED`.
- Summaries:
  - `SUMMARY_INTERVAL`, `SUMMARY_WINDOW`, `SUMMARY_MODEL`.
- Files:
  - `transcripts/session_YYYYmmdd_HHMMSS.jsonl`
  - `transcripts/session_YYYYmmdd_HHMMSS_summaries.jsonl`
  - `debug_audio/` for raw + Whisper input WAVs.

Whisper and RNNT load:

```python
whisper_model = WhisperModel(WHISPER_MODEL_NAME, device=device, compute_type=compute_type)

rnnt_model = ASRModel.from_pretrained(RNNT_MODEL_NAME, map_location=device)
# freeze + adjust preprocessor, then ONNXGreedyBatchedRNNTInfer
rnnt_decoding = ONNXGreedyBatchedRNNTInfer(RNNT_ONNX_ENCODER, RNNT_ONNX_DECODER, ...)
```

RNNT is **initialized** but currently the real‑time worker uses **Whisper only**; RNNT is available via `rnnt_transcribe_chunk()` if you want to switch.

Speaker model:

```python
speaker_model = get_speaker_model(threshold=SPEAKER_THRESHOLD, device=device)  # if SPEAKER_ID_ENABLED
```

#### 3.2.2 Queues, State, and WebSocket Handling

Global concurrency primitives:

- `audio_queue` – raw / structured audio chunks from mic or WebRTC.
- `interim_queue` – interim text payloads to be broadcast.
- `connected_clients` – active WebSocket clients.
- VAD and gating: `vad`, RMS, `last_voiced_ts`.
- Per‑speaker tracking:
  - `pending_per_speaker` – last ASR hypothesis waiting to be finalized.
  - `last_sent_per_speaker` – last final text.
  - `last_interim_per_speaker`, `interim_history_per_speaker`, `last_emitted_interim_text` – used for smooth interim streaming.
- `transcript_buffer` – sliding window of recent transcript/interim entries used by summarizer & LM correction.
- `stream_display_names` – mapping from `stream_id` to human display name.

WebSocket server:

- `start_websocket_server()` – `websockets.serve(handle_client, WEBSOCKET_HOST, WEBSOCKET_PORT)`.

`handle_client(websocket)` flow:

- On connect:
  - Add client to `connected_clients`.
  - Default `stream_id = STREAM_ID`, `lang = WHISPER_DEFAULT_LANGUAGE`.
- Message handling loop:
  - **Binary message (bytes):**
    - Interpret as float32 audio (`np.frombuffer`), ensure mono.
    - Update global RMS: `last_audio_level`.
    - Enqueue payload into `audio_queue` as `{"audio": audio, "stream_id": stream_id, "language": lang}`.
    - Optionally buffer raw audio for debug and save on disconnect to `debug_audio/raw_input_*.wav`.
  - **JSON text message:**
    - `{ "type": "config", "stream_id", "language" }` – update per‑connection stream id and language.
    - `{ "type": "register_user", "stream_id", "name" }` – map `stream_id` → human name in `stream_display_names`.

Frontends (Next.js or `client_test.py`) consume JSON messages of shape:

- Interim: `{ "type": "interim", "stream_id", "timestamp", "speaker", "text" }`
- Final transcript: `{ "type": "transcript", ... }`
- Summary: `{ "type": "summary" | "summary_final", "timestamp", "text" }`

`broadcast_json(obj)` sends JSON to all clients.

#### 3.2.3 Audio Capture from Local Mic (optional)

- `USE_LOCAL_MIC` (env) controls whether to use local `sounddevice` input.
- `audio_callback` computes RMS and pushes audio frames (float32) into `audio_queue`.
- `start_audio_stream()` selects device by `DEVICE_ID` (optionally restricted by `ALLOWED_INPUT_DEVICE_SUBSTRINGS`).

When `USE_LOCAL_MIC=True`, `main()` starts this stream in addition to handling WebRTC audio.

#### 3.2.4 Audio Pre‑processing and VAD

Helpers:

- `_float_to_int16_pcm(audio)` – convert float32 [-1,1] → int16 PCM.
- `normalize_audio(audio, target_rms=0.12, max_gain=3.0)` – normalize RMS with soft‑clipping and periodic logging.
- `apply_noise_suppression(audio)` – optional RNNoise denoiser controlled by `USE_RNNOISE`.
- `webrtc_vad_voiced_ratio(audio)` – compute fraction of 30 ms frames detected as voiced via WebRTC VAD.

These are used inside the transcription worker to gate out silence/noise and to stabilize input volume.

#### 3.2.5 Transcription Worker Thread

`transcribe_worker()` runs in a dedicated daemon thread:

1. Maintains a sliding buffer of recent audio samples.
2. For each item from `audio_queue`:
   - Normalize payload into `(buffer, stream_id, lang)`.
   - Append to buffer; keep up to ~3 seconds.
3. While `len(buffer) >= CHUNK_SIZE`:
   - Enforce `min_process_interval` to avoid over‑processing.
   - Extract `chunk_arr` of `CHUNK_SIZE` samples.
   - `normalize_audio` → `apply_noise_suppression` → `webrtc_vad_voiced_ratio` + RMS.
   - If VAD+RMS gate fails, skip and advance buffer by `CHUNK_ADVANCE`.
   - Apply optional `WHISPER_SPEEDUP_FACTOR` and `_resample_linear` to `TARGET_SR`.
   - Optionally write `whisper_input_*.wav` to `debug_audio/`.
   - Call `whisper_transcribe_chunk(resampled, lang)`.
   - Immediately block known hallucinations (`is_hallucination`) such as “thank you for watching…”.
   - Run lightweight NLP cleanup **inline**:
     - `process_interim_text(text, prev_final_text=last_emitted_interim, is_final=False)`, which applies the `nlp` rule‑based filters.
   - Estimate speaker label: `get_speaker_label(chunk_arr)` → diarization label.
   - Resolve display name: `resolve_speaker_name(stream_id, speaker_label)` using `stream_display_names`.
   - Update `pending_per_speaker` with latest hypothesis and stability counter.
   - Push a **partial** interim payload into `interim_queue` (Zoom‑style live typing box):

     ```json
     {
       "type": "interim",
       "stream_id": stream_id,
       "timestamp": ts,
       "speaker": display_speaker,
       "text": text
     }
     ```

   - If `INTERIM_ENABLED`, compute a throttled and possibly **stable prefix** version (`emit_text`) and also push that to `interim_queue`.

Result: frontend sees smooth, streaming interim captions with reduced flicker and hallucinations.

#### 3.2.6 Interim Broadcaster (live captions)

In `run_async()`:

```python
async def interim_broadcaster():
    while True:
        payload = interim_queue.get_nowait()
        await broadcast_json(payload)
        # also append to transcript_buffer with _ts
```

- Repeatedly drains `interim_queue` and sends interim messages to all WebSocket clients.
- Populates `transcript_buffer` with interim entries (`_ts` timestamps) so the summarizer has rolling context.

#### 3.2.7 Finalization Pipeline (`pending_flusher`) – Design vs. Current Mode

`pending_flusher()` is designed to:

- Periodically check `pending_per_speaker` for:
  - text that has been stable for enough time (`STABLE_ROUNDS_REQUIRED` and `DEBOUNCE_SECONDS`), or
  - segments to finalize after sustained silence (`SILENCE_FINALIZE_SEC`).
- Filter out very short / low‑alpha segments and hallucinations.
- Merge with longest interim seen for that speaker.
- Optionally run LM correction (`lm_correct_text`) if `LM_CORRECTION_ENABLED`.
- Format the segment using `nlp.formatting.format_segment()`.
- Append a `"transcript"` entry to `transcript_buffer` and `transcripts/*.jsonl`.
- Broadcast a final transcript payload:

```json
{
  "type": "transcript",
  "stream_id": stream_id,
  "timestamp": ts,
  "speaker": display_speaker,
  "text": corrected_text,
  "formatted": "[...]"
}
```

**Important:** In the current `run_async()` implementation, only `summarize_loop`, `interim_broadcaster`, and `level_monitor` are started. The log line explicitly states:

> `Final debounced transcripts disabled (interim-only mode).`

So by default:

- Frontend relies mainly on **interim** events (and its own gap‑based logic) to build history.
- The backend design supports final transcript messages and JSONL writing, but the finalizer task is not started. If you re‑enable `pending_flusher()` in `run_async()`, you will get true final transcript events and richer `transcripts/session_*.jsonl` content.

#### 3.2.8 Summarization Loop

`build_summarizer()` + `summarize_loop()`:

- `build_summarizer()`:
  - If `OPENAI_API_KEY` is available, creates an `OpenAI` client; otherwise summary is effectively disabled (no local BART inside this file – that exists only in `meeting_summary.py`).

- `_run_summary(client, local, text)`:
  - Uses OpenAI `chat.completions` (model `SUMMARY_MODEL`, default `gpt-4o-mini`) to produce meeting summary, or fallback to a local HuggingFace pipeline if provided.

- `summarize_loop()` (started in `run_async()`):
  - Every `SUMMARY_INTERVAL` seconds (default 300s = 5min):
    - Collects entries from `transcript_buffer` whose `_ts` lies in the last window.
    - Builds a compact `(speaker) text` transcript string.
    - Calls `_run_summary(...)`.
    - If a summary exists, writes `{"type":"summary", ...}` to `SUMMARY_FH` and broadcasts to clients.
  - On task cancellation (shutdown):
    - Generates a final overall summary (`type: "summary_final"`) over the full `transcript_buffer`.

The frontend shows rolling summaries and, when available, the final summary card.

#### 3.2.9 LM Correction (Optional)

`lm_correct_text(raw_text)` can:

1. Try external NLP microservice (`NLP_SERVICE_URL` → `/correct`).
2. Fallback to an OpenAI client (`LM_CORRECTION_MODEL`) for grammar/punctuation.

Currently this is **guarded** by `LM_CORRECTION_ENABLED` and is used in finalization (`pending_flusher`) when enabled.

---

## 4. NLP Pipeline (`nlp/` package)

Location: `nlp/`

Purpose: Provide **fast, deterministic, low‑latency** cleanup for streaming ASR text that can safely run on every interim.

### 4.1 Entry Point: `nlp/pipeline.py`

```python
from .filters.noise_filter import clean_noise
from .filters.repetition_filter import remove_overlap
from .filters.blocklist_filter import clean_blocklist
from .filters.trim_filter import trim_incomplete

rules = load_rules()  # from nlp/config/rules.json

text = clean_noise(text, rules["noise_patterns"])
text = remove_overlap(prev_final, text, rules["repetition"])
text = clean_blocklist(text, rules["blocklist"])
text = trim_incomplete(text, rules["trim"], is_final=is_final)
```

`process_interim_text(current_text, prev_final_text, is_final=False)` returns:

```json
{"final": bool, "text": "cleaned text"}
```

This function is called directly inside `realtime_transcriber.transcribe_worker()` for every chunk to:

- Strip noise annotations and timestamps.
- Merge overlapping ASR chunks cleanly.
- Remove hallucinated filler prefixes/suffixes like “yeah”, “thank you”.
- Trim half‑spoken trailing words during interim.

### 4.2 Rules: `nlp/config/rules.json`

Defines the runtime‑tunable patterns:

- `noise_patterns` – regexes for `(noise)`, `[applause]`, timestamps like `[00:01:23.456]`.
- `blocklist.prefixes` – tokens to remove at the **start** (e.g., `so`, `okay`, `ok`, `yeah`, `thank you`, `thanks`).
- `blocklist.suffixes` – tokens to strip from the **end**.
- `repetition.min_overlap_chars` – min characters for overlap detection.
- `trim.min_word_length` – minimum length for protected trailing words.

### 4.3 Filters

- `nlp/filters/noise_filter.py`
  - Compiles a combined regex from rules or defaults.
  - `clean_noise(text, custom_patterns)` removes noise annotations + timestamps and normalizes whitespace.

- `nlp/filters/blocklist_filter.py`
  - `clean_blocklist(text, config)`:
    - Normalizes phrases like `"thank you"` into word lists.
    - Repeatedly strips matching prefix/suffix phrases at boundaries.

- `nlp/filters/repetition_filter.py`
  - `remove_overlap(prev_final_text, current_text, config)`:
    - Finds the longest suffix of `prev` that matches a prefix of `current`.
    - If overlap is significant, merges text: `prev + suffix(current)`.
    - If no overlap, returns `current` as‑is (prevents weird concatenations).

- `nlp/filters/trim_filter.py`
  - `trim_incomplete(text, config, is_final=False)`:
    - For interim text: if the last word is short, alphabetic, and not in a set of common words, and likely half‑spoken, drop it.
    - For final text: returns as‑is.

### 4.4 Tests: `test_nlp_pipeline.py`

Contains unit tests verifying:

- Noise annotations and timestamps are removed.
- Overlap merging behaves as expected.
- Blocklist removes hallucinated prefixes.
- Half word trimming behaves correctly.

---

## 5. Speaker Diarization Pipeline

### 5.1 Core Model: `speaker.py`

Implements a reusable `SpeakerModel` for real‑time diarization using pyannote embeddings.

- Loads `pyannote/embedding` via `Model.from_pretrained("pyannote/embedding", use_auth_token=PYANNOTE_TOKEN)`.
- Maintains an in‑memory dictionary: `speaker_label → embedding`.
- For each new audio chunk:
  - Extract embedding (resampling to 16 kHz if needed).
  - Compare with existing profiles using cosine similarity.
  - If similarity ≥ `threshold` → reuse existing speaker label.
  - Else → create a new `"Speaker N"` profile.

Convenience functions:

- `get_speaker_model(threshold, device)` – global singleton instance.
- `identify_speaker(audio_chunk, pyannote_token)` – one‑shot identification.

### 5.2 Backend Integration

In `realtime_transcriber.py`:

- At startup (if `SPEAKER_ID_ENABLED`): `speaker_model = get_speaker_model(...)`.
- In `get_speaker_label(audio_chunk)`:
  - Calls `speaker_model.identify(chunk_arr, PYANNOTE_TOKEN)`.
  - On error or disabled, falls back to generic `"Speaker"`.
- `resolve_speaker_name(stream_id, speaker_label)`:
  - If frontend registered a user name for a given `stream_id`, use that instead of diarization label.

### 5.3 Secure Local Testing: `secure_speaker_test.py`

A CLI utility for local testing of speaker diarization **without any network**:

- Records several 5‑second segments from two people using `sounddevice`.
- Saves each to `recording_*.wav`, runs `speaker_model.identify()` on each.
- Prints which logical speaker label was assigned and the number of profiles.
- Cleans up WAV files at the end.

This is useful for validating that `PYANNOTE_TOKEN` and thresholds are configured correctly.

---

## 6. Summaries and Post‑Meeting Tools

### 6.1 Rolling + Final Summaries (Online)

Provided by `summarize_loop()` inside `realtime_transcriber.py`:

- Uses `transcript_buffer` (interim +, when enabled, final entries) with `_ts` timestamps.
- Every `SUMMARY_INTERVAL` seconds:
  - Gathers recent text window.
  - Calls `_run_summary` → OpenAI `SUMMARY_MODEL`.
  - Broadcasts a `{"type": "summary"}` payload and appends to `SUMMARY_PATH`.
- On shutdown, emits a `"summary_final"` payload over the full session.

The frontend shows these in the right sidebar (`summaries` list + full summary view).

### 6.2 Offline Full Summary: `meeting_summary.py`

This script builds a final markdown summary from `transcripts/session_*.jsonl`.

Flow:

1. `load_transcripts(path)` → list of transcript entries.
2. Build text:

   ```text
   [HH:MM:SS] (Speaker) text
   ```

3. `build_summarizer(prefer)`:
   - If `prefer` is `openai` or `auto`, tries OpenAI client.
   - Else if `bart` or `auto`, tries local `facebook/bart-large-cnn` pipeline.
4. `summarize_text(client, local, text, model)`:
   - Uses OpenAI chat or local BART to generate final summary text.
5. Writes `*_final_summary.md` next to the transcript file.

Invoked as:

```bash
python meeting_summary.py --input transcripts/session_....jsonl --prefer auto
```

---

## 7. Frontend Architecture (`frontend_dashboard/`)

This is a single‑page Next.js app (`pages/index.js`) that connects to both:

- The **ASR WebSocket** (`ws://localhost:8765` by default), and
- The **WebRTC ingest signaling** endpoint (`SIGNAL_URL`, default `http://localhost:8081/offer`).

### 7.1 State Model

Main React state (simplified):

- Transcript and summaries:
  - `lines` – list of past transcript entries (`type: "transcript"`).
  - `summaries` – rolling summaries.
  - `fullSummary` – final meeting summary.
  - `summaryView` – `"list"` or `"full"`.
- Live captioning and connection:
  - `live` – current live interim segment.
  - `subtitle` / `subtitleMode` – for subtitle‑style display (currently inline).
  - `connected` – WebSocket connection to ASR backend.
  - `webrtcStatus` – WebRTC connection state (`connecting`, `connected`, `failed`, etc.).
  - `micOn`, `camOn` – toggles.
  - `elapsedSeconds` – timer for duration of live session.
- Identity and devices:
  - `displayName` – user name.
  - `wsUrl` – ASR backend WebSocket URL.
  - `devices`, `selectedDeviceId`, `permissionGranted` – audio devices and mic permission.
  - `participants` – set of speakers currently active on the call, colored via `palette`.

Refs: `wsRef`, `pcRef` (RTCPeerConnection), `mediaStreamRef`, `audioCtxRef`, etc.

### 7.2 WebSocket Connection to Backend

`connect(url)`:

- Opens `new WebSocket(url)`.
- On `open`:
  - Sends `{"type":"config","stream_id":...,"language":"en"}`.
  - Sends `{"type":"register_user","stream_id":...,"name": displayName}` if available.
- On `message`:
  - Parses JSON and updates state:
    - `type === "interim"`:
      - Updates `participants` and last activity timestamps.
      - Maintains a `live` box and heuristically segments utterances based on gaps (`SILENCE_GAP_MS`).
      - Keeps a separate `subtitle` aggregation to reduce flicker.
    - `type === "transcript"`:
      - Clears `live` and pushes entry into `lines`.
    - `type === "summary"`:
      - Prepends to `summaries` list.
    - `type === "summary_final"`:
      - Stores in `fullSummary` and allows switching to the full summary view.

`disconnect()` simply closes the WebSocket and clears flags.

### 7.3 WebRTC Mic Capture and Ingest

Two paths are implemented:

1. **Preferred path – WebRTC to `webrtc_ingest.py`:**

   - `startWebRtc()`:
     - Ensures mic permission (via `getUserMedia`).
     - Creates `RTCPeerConnection` and adds all audio tracks.
     - Gathers ICE candidates and then POSTs SDP offer to `SIGNAL_URL` (`/offer`).
     - Applies answer SDP to the peer connection.
     - Updates `webrtcStatus` accordingly.
   - `stopWebRtc()` closes PC and stops mic tracks.
   - A `useEffect` watches `micOn` + `connected` and auto‑starts/stops WebRTC.

2. **Direct WebSocket mic streaming (legacy / secondary path):**

   - `startMicStream()` uses Web Audio API:
     - Captures mic at 48 kHz.
     - Feeds samples from a `ScriptProcessorNode` directly to `wsRef` as `ArrayBuffer` of Float32.
   - `stopMicStream()` tears down the audio graph.

In practice, the main flow in this repo now uses the **WebRTC ingest path**, because it handles normalization and speedup in Python.

### 7.4 UI Layout

- Header:
  - Shows connection status, backend WS URL, Connect/Disconnect, theme toggle.
- Participants row:
  - Displays speaker badges with colors and active status.
- Live "You are saying" strip:
  - Shows current `live.text` while interim is streaming.
- Center stage:
  - Zoom‑style grid placeholders showing participant initials.
- Right sidebar:
  - **Live Transcript panel**:
    - Optionally shows current `live` entry at the top.
    - Scrollable list of `lines` (past transcript items).
  - **Summaries panel**:
    - List of rolling summaries or a single full summary card.

---

## 8. Non‑Real‑Time ASR Service: `asr_api.py`

This is a standalone FastAPI app exposing a simple HTTP API for full file transcription (not streaming):

- `GET /health` → `{ "status": "ok" }`.
- `POST /transcribe-file` with `UploadFile` and optional `language`:
  - Reads entire file into memory.
  - Uses `soundfile` (`sf.read`) to decode to float32 mono audio.
  - Resamples to `TARGET_SR` (16 kHz) using `_resample_linear` imported from `realtime_transcriber`.
  - Runs `whisper_model.transcribe(...)` once over full audio.
  - Concatenates all segment texts into a single string.
  - Returns `{ "text": text, "language": lang }`.

This API reuses the same Whisper model instance and resampling logic as the real‑time backend.

---

## 9. Legacy / Prototype NLP Modules

These modules represent an older NLP pipeline. Their functions are largely commented out and replaced by the new `nlp/` package:

- `cleaner.py` – older noise/filler removal logic.
- `repeat_remove.py` – older repetition/hallucination handling.
- `finalizer.py` – older hallucination blocklist and punctuation normalization.
- `nlp_service.py` – FastAPI service composing `cleaner`, `repeat_remove`, and `finalizer` into a `/correct` endpoint.

They remain in the repo for reference but **are not active** in the current main pipeline.

---

## 10. RNNT Model Tools

- `list_nemo_rnnt_models.py`
  - Lists available NeMo ASR RNNT/Conformer models containing `"transducer"` or `"rnnt"`.

- `rnnt_export_and_quantize.py`
  - Exports a NeMo RNNT model to ONNX and applies dynamic INT8 quantization:
    - `export_rnnt_onnx` → `rnnt_conformer_small.onnx`.
    - `quantize_to_int8` for full RNNT graph or separated `encoder-rnnt_conformer_small.onnx`, `decoder_joint-rnnt_conformer_small.onnx`.
  - Produces the ONNX files used by `realtime_transcriber.py` (`RNNT_ONNX_ENCODER`, `RNNT_ONNX_DECODER`).

These tools are **offline utilities** for preparing faster CPU‑friendly RNNT models; the main streaming path currently uses Whisper.

---

## 11. Diagnostics and Test Utilities

- `mic_check.py`
  - Prints available audio devices and default input sample rate.
  - Helps determine `DEVICE_ID` and verify audio setup.

- `client_test.py`
  - Simple WebSocket client that connects to `ws://localhost:8765` and logs `interim`, `transcript`, and `summary` messages.

- `test_speaker.py`, `test_speaker_file.py`, `test_speaker_real.py`, `test_speaker_sensitive.py`
  - Various tests and demos for the `speaker.py` module.

- `debug_audio/`
  - Directory where the backend writes:
    - Raw WebRTC input (`raw_input_*.wav`).
    - Whisper input chunks (`whisper_input_*.wav`).
  - Used for debugging audio quality and hallucination issues.

---

## 12. File‑by‑File Status (Functional vs Prototype)

### Core Runtime (Functional)

- `realtime_transcriber.py` – **Main ASR + NLP + summarization backend (WebSocket)**.
- `webrtc_ingest.py` – **WebRTC ingest service (HTTP /offer → WS to ASR)**.
- `frontend_dashboard/pages/index.js` – **Main Next.js UI**.
- `speaker.py` – **Speaker diarization model used in backend**, plus helpers.
- `nlp/` (pipeline + filters + rules.json) – **Active NLP cleanup pipeline**.
- `meeting_summary.py` – **Offline summarization CLI** for saved transcripts.
- `asr_api.py` – **Functional FastAPI service** for non‑real‑time file transcription.

### Optional / Disabled by Default

- `nlp_service.py` – NLP microservice implementation **commented out**; used only if re‑enabled and `NLP_SERVICE_URL` is set.
- `pending_flusher()` in `realtime_transcriber.py` – final transcript emission **implemented but not started** in `run_async()` (current mode is interim‑only).

### Prototypes / Legacy

- `realtime_transcription_prototype.py` – older all‑in‑one prototype with WebSocket + matplotlib visualizer.
- `cleaner.py`, `repeat_remove.py`, `finalizer.py` – legacy NLP components superseded by `nlp/`.

### Tools & Tests

- `client_test.py`, `mic_check.py`, `secure_speaker_test.py`, `test_nlp_pipeline.py`, `test_speaker*.py`, `webrtc_ingest.py` (tuning), RNNT export scripts.

---

## 13. Summary of Key Pipelines

### 13.1 Real‑Time Meeting Pipeline (End‑to‑End)

1. **User opens frontend** (`frontend_dashboard`, `npm run dev` → http://localhost:3000).
2. User clicks **Connect** → frontend connects WebSocket to `ws://localhost:8765`.
3. Mic permission is granted; `startWebRtc()` creates WebRTC `RTCPeerConnection`.
4. Browser sends SDP offer to `SIGNAL_URL` (`http://localhost:8081/offer`).
5. `webrtc_ingest.py` completes handshake and starts receiving Opus/PCM audio.
6. `webrtc_ingest` normalizes + resamples audio and sends 20 ms float32 chunks to ASR backend via WebSocket.
7. `realtime_transcriber`:
   - Ingests audio into `audio_queue`.
   - `transcribe_worker` runs VAD + preprocessing + Whisper ASR.
   - Applies NLP pipeline (`nlp`) and speaker ID (`speaker.py`).
   - Emits interim captions via `interim_queue` → `interim_broadcaster` → WebSocket JSON.
   - Maintains `transcript_buffer` for summarization.
8. `summarize_loop` periodically generates rolling summaries and a final summary using OpenAI.
9. Frontend displays:
   - Live caption box (`live`).
   - Transcript history (`lines`).
   - Rolling summaries (`summaries`).
   - Final full summary (`fullSummary`).
10. Optionally, JSONL transcripts and summary files are written under `transcripts/` for offline analysis.

### 13.2 Offline File Transcription Pipeline

1. Start `asr_api.py` (e.g., via `uvicorn`).
2. Client uploads an audio file to `/transcribe-file`.
3. Service decodes + resamples audio and runs Whisper once over the full track.
4. Returns final text as a single string.

---

This document should give you a complete mental model of **where every major piece lives**, how data flows between frontend and backend, what each pipeline does, and which components are active vs. experimental.
