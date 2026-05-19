import asyncio
import websockets
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from sklearn.metrics.pairwise import cosine_similarity
import torch, queue, time, threading, difflib, os
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import webrtcvad

# -------------------------------
# CONFIG (tune these)
# -------------------------------
SAMPLE_RATE = 16000
DEVICE_ID = int(os.getenv("DEVICE_ID", "1"))
CHUNK_DURATION = 0.8
OVERLAP_DURATION = 0.3
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
OVERLAP_SIZE = int(SAMPLE_RATE * OVERLAP_DURATION)
WEBSOCKET_PORT = 8765

"""
 Device security: allow only physical microphones to be used.
 Leave list empty to allow any device. To enforce, put substrings like ["Microphone", "Realtek"]
"""
ALLOWED_INPUT_DEVICE_SUBSTRINGS = []

# VAD / silence gating (WebRTC VAD)
VAD_AGGRESSIVENESS = 2  # 0-3 (3 is most aggressive)
VAD_MIN_VOICED_RATIO = 0.5  # proportion of frames that must be voiced in a chunk

# Visualizer toggle (GUI runs on main thread in production)
ENABLE_VISUALIZER = os.getenv("ENABLE_VISUALIZER", "1") == "1"

# duplicate suppression & debounce
DUPLICATE_SIMILARITY = 0.88
DEBOUNCE_SECONDS = 0.6
RECENT_MESSAGE_TTL = 10.0

# speaker matching
SPEAKER_THRESHOLD = 0.75

# -------------------------------
# LOAD MODELS
# -------------------------------
print("Loading models...")
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "int8" if device == "cpu" else "float16"
whisper_model = WhisperModel("base.en", device=device, compute_type=compute_type)
print(f"✅ Whisper loaded on {device.upper()} ({compute_type})")

# Optional speaker embedding (secure token from env)
PYANNOTE_TOKEN = os.getenv("PYANNOTE_TOKEN")
speaker_embedder = None
if PYANNOTE_TOKEN:
    try:
        from pyannote.audio import Model
        speaker_embedder = Model.from_pretrained("pyannote/embedding", token=PYANNOTE_TOKEN).to(device)
        print("✅ Speaker embedding model loaded")
    except Exception as e:
        print("⚠️ Speaker embedding disabled:", e)
else:
    print("ℹ️ PYANNOTE_TOKEN not set. Speaker identification disabled.")

# -------------------------------
# AUDIO CAPTURE
# -------------------------------
audio_queue = queue.Queue()
connected_clients = set()
last_audio_level = 0.0

def audio_callback(indata, frames, time_info, status):
    global last_audio_level
    if status:
        print("Audio status:", status)
    try:
        lvl = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
    except Exception:
        lvl = 0.0
    last_audio_level = lvl
    audio_queue.put(indata.copy())

def start_audio_stream():
    # Optional device allowlist enforcement
    try:
        dev_info = sd.query_devices(DEVICE_ID)
        dev_name = dev_info.get("name", "")
        if ALLOWED_INPUT_DEVICE_SUBSTRINGS:
            if not any(s in dev_name for s in ALLOWED_INPUT_DEVICE_SUBSTRINGS):
                raise RuntimeError(f"Input device not allowed: {dev_name}")
    except Exception as e:
        print("⚠️ Device check:", e)

    # Try requested device first, then fall back to default device on failure
    try:
        stream = sd.InputStream(
            device=DEVICE_ID,
            channels=1,
            samplerate=SAMPLE_RATE,
            dtype="float32",
            callback=audio_callback,
        )
        stream.start()
        print(f"🎧 Audio stream started (device={DEVICE_ID}, sr={SAMPLE_RATE}).")
        return stream
    except Exception as e:
        print("⚠️ Failed to open requested input device, falling back to default:", e)
        stream = sd.InputStream(
            channels=1,
            samplerate=SAMPLE_RATE,
            dtype="float32",
            callback=audio_callback,
        )
        stream.start()
        print(f"🎧 Audio stream started (default input device, sr={SAMPLE_RATE}).")
        return stream

# -------------------------------
# SPEAKER ID LOGIC
# -------------------------------
speaker_profiles = {}

def embed_speaker(audio_chunk: np.ndarray):
    if speaker_embedder is None:
        return None
    waveform = torch.from_numpy(audio_chunk.astype(np.float32)).to(device)
    if waveform.dim() == 1:
        waveform = waveform.unsqueeze(0)
    with torch.no_grad():
        emb = speaker_embedder(waveform)
    return emb.cpu().numpy()

def get_speaker_label(audio_chunk: np.ndarray):
    emb = embed_speaker(audio_chunk)
    if emb is None:
        return "SPEAKER"
    if len(speaker_profiles) == 0:
        label = "SPEAKER_1"
        speaker_profiles[label] = emb
        return label
    sims = {spk: cosine_similarity(emb, vec)[0,0] for spk, vec in speaker_profiles.items()}
    best_spk, best_sim = max(sims.items(), key=lambda x: x[1])
    if best_sim > SPEAKER_THRESHOLD:
        return best_spk
    else:
        new_label = f"SPEAKER_{len(speaker_profiles)+1}"
        speaker_profiles[new_label] = emb
        return new_label

# -------------------------------
# DEDUP, DEBOUNCE, RECENT MESSAGES
# -------------------------------
pending_per_speaker = {}
last_sent_per_speaker = {}
recent_messages = []

def is_recent_duplicate(text: str):
    now = time.time()
    for t, ts in recent_messages:
        if now - ts > RECENT_MESSAGE_TTL:
            continue
        ratio = difflib.SequenceMatcher(None, t, text).ratio()
        if ratio >= DUPLICATE_SIMILARITY:
            return True
    return False

def add_recent_message(text: str):
    now = time.time()
    recent_messages.append((text, now))
    while recent_messages and (now - recent_messages[0][1] > RECENT_MESSAGE_TTL):
        recent_messages.pop(0)

# -------------------------------
# UTILITIES
# -------------------------------
def rms(audio: np.ndarray):
    return float(np.sqrt(np.mean(np.square(audio.astype(np.float32)))))

def _float_to_int16_pcm(audio: np.ndarray) -> bytes:
    a = np.clip(audio, -1.0, 1.0)
    a = (a * 32767.0).astype(np.int16)
    return a.tobytes()

def webrtc_vad_voiced_ratio(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> float:
    """
    Split into 30ms frames and run WebRTC VAD. Returns ratio of voiced frames.
    """
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    frame_ms = 30
    frame_len = int(sample_rate * frame_ms / 1000)
    pcm = _float_to_int16_pcm(audio)
    # iterate over frames
    voiced = 0
    total = 0
    for i in range(0, len(pcm), frame_len * 2):
        frame = pcm[i:i + frame_len * 2]
        if len(frame) < frame_len * 2:
            break
        is_voiced = vad.is_speech(frame, sample_rate)
        voiced += 1 if is_voiced else 0
        total += 1
    return (voiced / total) if total else 0.0

# -------------------------------
# REAL-TIME VISUALIZATION (matplotlib)
# -------------------------------
history_len = 2000
audio_history = deque(maxlen=history_len)
rms_history = deque(maxlen=200)
voiced_ratio_history = deque(maxlen=200)

def update_plot(frame):
    if not audio_queue.empty():
        samples = audio_queue.queue[-1].squeeze()
        audio_history.extend(samples[-len(samples):])
        r = rms(np.array(audio_history))
        rms_history.append(r)

        # Compute voiced ratio on a recent window (e.g., last CHUNK_SIZE)
        recent = np.array(list(audio_history)[-CHUNK_SIZE:]) if len(audio_history) >= CHUNK_SIZE else np.array(list(audio_history))
        vr = webrtc_vad_voiced_ratio(recent, SAMPLE_RATE) if len(recent) > 0 else 0.0
        voiced_ratio_history.append(vr)

        ax1.clear()
        ax2.clear()

        ax1.plot(list(audio_history))
        ax1.set_ylim(-1, 1)
        ax1.set_title("Live Audio Waveform")
        ax1.set_ylabel("Amplitude")

        ax2.plot(list(voiced_ratio_history), label="Voiced ratio", linewidth=1.2)
        ax2.axhline(VAD_MIN_VOICED_RATIO, color='r', linestyle='--', label='VAD voiced threshold')
        ax2.set_ylim(0, 1)
        ax2.set_title("WebRTC VAD Voiced Ratio")
        ax2.set_ylabel("Ratio (0-1)")
        ax2.legend(loc='upper right')

    plt.tight_layout()

def start_visualizer():
    global fig, ax1, ax2
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))
    ani = animation.FuncAnimation(fig, update_plot, interval=100, cache_frame_data=False)
    plt.show()

# -------------------------------
# TRANSCRIPTION WORKER (background thread)
# -------------------------------
def transcribe_worker(loop):
    buffer = np.zeros((0,1), dtype=np.float32)
    while True:
        data = audio_queue.get()
        buffer = np.concatenate((buffer, data), axis=0)
        max_buf = SAMPLE_RATE * 4
        if len(buffer) > max_buf:
            buffer = buffer[-max_buf:]
        if len(buffer) >= CHUNK_SIZE:
            start_idx = max(0, len(buffer) - (CHUNK_SIZE + OVERLAP_SIZE))
            chunk_arr = buffer[start_idx : start_idx + CHUNK_SIZE + OVERLAP_SIZE].squeeze()
            # WebRTC VAD gate
            voiced_ratio = webrtc_vad_voiced_ratio(chunk_arr, SAMPLE_RATE)
            if voiced_ratio < VAD_MIN_VOICED_RATIO:
                continue
            if np.allclose(chunk_arr, 0, atol=1e-4):
                continue

            try:
                segments, _ = whisper_model.transcribe(
                    chunk_arr,
                    language="en",
                    beam_size=1,
                    vad_filter=True,
                    condition_on_previous_text=False,
                )
                text = " ".join(seg.text for seg in segments).strip()
                if not text:
                    continue
                speaker_label = get_speaker_label(chunk_arr)
                now = time.time()
                prev_pending = pending_per_speaker.get(speaker_label)
                if prev_pending:
                    prev_text = prev_pending['text']
                    if len(text) < len(prev_text):
                        ratio = difflib.SequenceMatcher(None, prev_text, text).ratio()
                        if ratio < 0.95:
                            pending_per_speaker[speaker_label] = {'text': text, 'ts': now}
                    else:
                        pending_per_speaker[speaker_label] = {'text': text, 'ts': now}
                else:
                    pending_per_speaker[speaker_label] = {'text': text, 'ts': now}
            except Exception as e:
                print("Transcription error:", e)

# -------------------------------
# BACKGROUND FLUSHER (async)
# -------------------------------
async def pending_flusher():
    while True:
        now = time.time()
        to_send = []
        for spk, entry in list(pending_per_speaker.items()):
            age = now - entry['ts']
            if age >= DEBOUNCE_SECONDS:
                text = entry['text'].strip()
                pending_per_speaker.pop(spk, None)
                if len(text) < 2:
                    continue
                last = last_sent_per_speaker.get(spk)
                if last:
                    last_text, last_ts = last
                    ratio = difflib.SequenceMatcher(None, last_text, text).ratio()
                    if ratio >= DUPLICATE_SIMILARITY and (now - last_ts) < RECENT_MESSAGE_TTL:
                        continue
                if is_recent_duplicate(text):
                    continue
                to_send.append((spk, text))
        for spk, text in to_send:
            ts_str = time.strftime("%H:%M:%S")
            msg = f"[{ts_str}] ({spk}) {text}"
            print("🗣️", msg)
            last_sent_per_speaker[spk] = (text, time.time())
            add_recent_message(text)
            asyncio.create_task(broadcast_message(msg))
        await asyncio.sleep(0.12)


async def level_monitor():
    """Periodically print audio level and queue size so we know the mic is active."""
    while True:
        try:
            print(f"[monitor] RMS={last_audio_level:.4f} | queue={audio_queue.qsize()} | pending={len(pending_per_speaker)}")
        except Exception:
            pass
        await asyncio.sleep(2.0)

# -------------------------------
# WEBSOCKET SERVER
# -------------------------------
async def broadcast_message(message):
    if connected_clients:
        await asyncio.gather(
            *[ws.send(message) for ws in list(connected_clients)],
            return_exceptions=True
        )

async def handle_client(websocket):
    print("Client connected:", websocket.remote_address)
    connected_clients.add(websocket)
    try:
        async for _ in websocket:
            pass
    except websockets.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        print("Client disconnected")

async def start_websocket_server():
    server = await websockets.serve(handle_client, "0.0.0.0", WEBSOCKET_PORT)
    print(f"🌐 WebSocket server at ws://localhost:{WEBSOCKET_PORT}/")
    await server.wait_closed()

# -------------------------------
# MAIN (production-ready: WebSocket in thread, GUI on main)
# -------------------------------
def run_async_server(loop):
    """Run WebSocket server and async tasks in background thread."""
    asyncio.set_event_loop(loop)
    loop.create_task(pending_flusher())
    loop.create_task(level_monitor())
    loop.run_until_complete(start_websocket_server())

def main():
    stream = start_audio_stream()
    print("🎤 Mic started (Ctrl+C to stop)")
    
    # Create event loop for async server
    loop = asyncio.new_event_loop()  
    
    # Start transcription worker thread
    threading.Thread(target=transcribe_worker, args=(loop,), daemon=True).start()
    
    # Start WebSocket server in background thread
    server_thread = threading.Thread(target=run_async_server, args=(loop,), daemon=True)
    server_thread.start()
    
    try:
        if ENABLE_VISUALIZER:
            # Run matplotlib on main thread (production-readyy)
            print("📊 Starting visualizer on main thread...")
            start_visualizer()  # Blocks on main thread
        else:
            # If no visualizer, just keep main thread alivee
            print("ℹ️ Visualizer disabled. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        stream.stop()
        stream.close()
        loop.call_soon_threadsafe(loop.stop)

if __name__ == "__main__":
    main()
