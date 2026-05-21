import asyncio
import websockets
import httpx
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from sklearn.metrics.pairwise import cosine_similarity
import torch, queue, time, threading, difflib, os, json
import webrtcvad
from collections import deque
try:
    from nemo.collections.asr.models import ASRModel
    from nemo.collections.asr.parts.submodules.rnnt_greedy_decoding import ONNXGreedyBatchedRNNTInfer
except ImportError:
    ASRModel = None
    ONNXGreedyBatchedRNNTInfer = None
from datetime import datetime
from pathlib import Path
import wave
from nlp.pipeline import process_interim_text
from nlp.formatting import format_segment
from nlp.translator import get_translator
from speaker import get_speaker_model

try:
    import rnnoise  # optional; used when USE_RNNOISE is True
except Exception:
    rnnoise = None

import warnings
try:
    import torchaudio as _ta
    # Handle newer torchaudio versions where set_audio_backend is deprecated
    if hasattr(_ta, "set_audio_backend"):
        try:
            _ta.set_audio_backend("soundfile")
        except Exception:
            pass  # set_audio_backend deprecated in newer versions
except Exception:
    _ta = None

warnings.filterwarnings("ignore", message="Input tensor was 2D.*", module="asteroid_filterbanks.*")
warnings.filterwarnings("ignore", message="torchaudio.set_audio_backend.*", module=".*")

SAMPLE_RATE = 16000
DEVICE_ID = int(os.getenv("DEVICE_ID", "1"))
# Use a slightly longer chunk by default so Whisper gets more context than the first ~0.9s
CHUNK_DURATION = float(os.getenv("CHUNK_DURATION", "3.0"))
OVERLAP_DURATION = float(os.getenv("OVERLAP_DURATION", "0.6"))
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
OVERLAP_SIZE = int(SAMPLE_RATE * OVERLAP_DURATION)
CHUNK_ADVANCE = CHUNK_SIZE - OVERLAP_SIZE
TARGET_SR = 16000
STREAM_ID = "local"  # default stream id used if none provided by client
USE_RNNOISE = os.getenv("USE_RNNOISE", "False").lower() in {"1", "true", "yes"}
USE_LOCAL_MIC = os.getenv("USE_LOCAL_MIC", "False").lower() in {"1", "true", "yes"}
PUNCTUATION_ENABLED = False
INTERIM_ENABLED = True
INTERIM_MIN_INTERVAL = float(os.getenv("INTERIM_MIN_INTERVAL", "0.15"))
INTERIM_SIMILARITY_SKIP = float(os.getenv("INTERIM_SIMILARITY_SKIP", "0.98"))
INTERIM_USE_STABLE_PREFIX = False
INTERIM_PREFIX_DEPTH = 3
INTERIM_REQUIRE_WORD_BOUNDARY = False
INTERIM_MIN_CHARS_DELTA = 0
# Gate applies to full ASR chunks (~3s), not per tiny WebSocket frame.
RMS_MIN_LEVEL = float(os.getenv("RMS_MIN_LEVEL", "0.00025"))
VAD_MIN_VOICED_RATIO = float(os.getenv("VAD_MIN_VOICED_RATIO", "0.06"))
MIN_SEGMENT_LOGPROB = float(os.getenv("MIN_SEGMENT_LOGPROB", "-1.25"))
MAX_NO_SPEECH_PROB = float(os.getenv("MAX_NO_SPEECH_PROB", "0.85"))
WHISPER_SPEEDUP_FACTOR = float(os.getenv("WHISPER_SPEEDUP_FACTOR", "1.0"))
DECODE_BEAM_SIZE = int(os.getenv("DECODE_BEAM_SIZE", "1"))
MAX_AUDIO_QUEUE = int(os.getenv("MAX_AUDIO_QUEUE", "120"))
CLIENT_INPUT_SAMPLE_RATE = int(os.getenv("CLIENT_INPUT_SAMPLE_RATE", "48000"))
NO_SPEECH_THRESHOLD = 0.6
LOGPROB_MIN = -0.4
STABLE_SIMILARITY_FINAL = 0.98
STABLE_ROUNDS_REQUIRED = 1
MIN_ALPHA_FINAL = int(os.getenv("MIN_ALPHA_FINAL", "5"))
MIN_WORDS_FINAL = int(os.getenv("MIN_WORDS_FINAL", "1"))
SILENCE_FINALIZE_SEC = float(os.getenv("SILENCE_FINALIZE_SEC", "1.5"))
WEBSOCKET_PORT = int(os.getenv("PORT", os.getenv("WEBSOCKET_PORT", "8765")))
WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
ALLOWED_INPUT_DEVICE_SUBSTRINGS = []
VAD_AGGRESSIVENESS = int(os.getenv("VAD_AGGRESSIVENESS", "2"))
DUPLICATE_SIMILARITY = 0.95
DEBOUNCE_SECONDS = 0.35
RECENT_MESSAGE_TTL = 10.0
SPEAKER_THRESHOLD = 0.75
SPEAKER_ID_ENABLED = os.getenv("SPEAKER_ID_ENABLED", "False").lower() in {"1", "true", "yes"}
SUMMARY_INTERVAL = int(os.getenv("SUMMARY_INTERVAL", "5"))
SUMMARY_WINDOW = int(os.getenv("SUMMARY_WINDOW", "5"))
AUTH_API_URL = os.getenv("AUTH_API_URL", "http://localhost:8200")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key-change-me")
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "gpt-4o-mini")
LM_CORRECTION_MODEL = os.getenv("LM_CORRECTION_MODEL", "gpt-4o-mini")
LM_CORRECTION_ENABLED = os.getenv("LM_CORRECTION_ENABLED", "").lower() in {"1", "true", "yes"}
NLP_SERVICE_URL = os.getenv("NLP_SERVICE_URL", "")
_lang_env = (os.getenv("WHISPER_LANGUAGE", "auto") or "auto").strip().lower()
WHISPER_DEFAULT_LANGUAGE = None if _lang_env in {"", "auto"} else _lang_env
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base.en")
WHISPER_INITIAL_PROMPT = os.getenv(
    "WHISPER_INITIAL_PROMPT",
    "Live meeting. Speakers use English and Hindi. Transcribe exactly what is said.",
)
SESSION_START = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_DIR = Path("transcripts")
OUT_DIR.mkdir(parents=True, exist_ok=True)
TRANSCRIPT_PATH = OUT_DIR / f"session_{SESSION_START}.jsonl"
SUMMARY_PATH = OUT_DIR / f"session_{SESSION_START}_summaries.jsonl"

# Audio debugging
DEBUG_AUDIO_DIR = Path("debug_audio")
DEBUG_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
# Default off; enable by setting env RECORD_DEBUG_AUDIO=true when you need wav dumps
RECORD_DEBUG_AUDIO = os.getenv("RECORD_DEBUG_AUDIO", "False").lower() in {"1", "true", "yes"}

requested_device = os.getenv("WHISPER_DEVICE", "auto").lower()
if requested_device in {"cpu", "cuda"}:
    if requested_device == "cuda" and not torch.cuda.is_available():
        device = "cpu"
    else:
        device = requested_device
else:
    device = "cuda" if torch.cuda.is_available() else "cpu"

# Default to a more CPU-friendly compute type and thread count when on CPU.
if device == "cpu" and "OMP_NUM_THREADS" not in os.environ:
    os.environ["OMP_NUM_THREADS"] = "8"
default_compute = "int8" if device == "cpu" else "float16"
compute_type = os.getenv("WHISPER_COMPUTE_TYPE", default_compute)

print(f"Whisper device: {device.upper()} | compute_type={compute_type} | model={WHISPER_MODEL_NAME}")
whisper_model = WhisperModel(WHISPER_MODEL_NAME, device=device, compute_type=compute_type)
RNNT_MODEL_NAME = os.getenv("RNNT_MODEL", "stt_en_conformer_transducer_small")
RNNT_ONNX_ENCODER = os.getenv("RNNT_ONNX_ENCODER", "encoder-rnnt_conformer_small_int8.onnx")
RNNT_ONNX_DECODER = os.getenv("RNNT_ONNX_DECODER", "decoder_joint-rnnt_conformer_small_int8.onnx")
RNNT_MAX_SYMBOLS_PER_STEP = int(os.getenv("RNNT_MAX_SYMBOLS_PER_STEP", "5"))

rnnt_model = None
rnnt_decoding = None
try:
    if ASRModel is None or ONNXGreedyBatchedRNNTInfer is None:
        raise ImportError("nemo-toolkit not installed; RNNT disabled (Whisper-only mode)")
    print(f"RNNT: loading NeMo model {RNNT_MODEL_NAME} for tokenizer and preprocessor...")
    rnnt_model = ASRModel.from_pretrained(RNNT_MODEL_NAME, map_location=device)
    rnnt_model.freeze()
    try:
        rnnt_model.preprocessor.featurizer.dither = 0.0
    except Exception:
        pass
    try:
        rnnt_model.preprocessor.featurizer.pad_to = 0
    except Exception:
        pass
    print(
        f"RNNT: initializing ONNXGreedyBatchedRNNTInfer with encoder={RNNT_ONNX_ENCODER}, "
        f"decoder={RNNT_ONNX_DECODER}"
    )
    rnnt_decoding = ONNXGreedyBatchedRNNTInfer(
        RNNT_ONNX_ENCODER,
        RNNT_ONNX_DECODER,
        RNNT_MAX_SYMBOLS_PER_STEP,
    )
except Exception as e:
    rnnt_model = None
    rnnt_decoding = None
    try:
        print(f"RNNT init failed: {type(e).__name__}: {e}")
    except Exception:
        pass
def _load_dotenv_file(path: Path) -> None:
    """Load KEY=VALUE lines from .env into os.environ (only if not already set)."""
    if not path.exists():
        return
    try:
        for ln in path.read_text(encoding="utf-8").splitlines():
            s = (ln or "").strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            key, val = s.split("=", 1)
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:
        pass


PYANNOTE_TOKEN = os.getenv("PYANNOTE_TOKEN") or os.getenv("HF_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
_load_dotenv_file(Path(".env"))
PYANNOTE_TOKEN = os.getenv("PYANNOTE_TOKEN") or os.getenv("HF_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if PYANNOTE_TOKEN is None or OPENAI_API_KEY is None:
    try:
        p = Path("tokenHF.txt")
        if p.exists():
            try:
                lines = p.read_text(encoding="utf-8").splitlines()
            except Exception:
                lines = []
            for ln in lines:
                s = (ln or "").strip()
                if not s:
                    continue
                if PYANNOTE_TOKEN is None:
                    if s.startswith("HF_TOKEN="):   
                        val = s.split("=", 1)[1].strip()
                        if val.startswith("hf_"):
                            PYANNOTE_TOKEN = val
                    elif s.startswith("hf_"):
                        PYANNOTE_TOKEN = s
                if OPENAI_API_KEY is None:
                    if s.lower().startswith("open_ai=") or s.lower().startswith("openai_api_key="):
                        val = s.split("=", 1)[1].strip()
                        if val:
                            OPENAI_API_KEY = val
    except Exception:
        pass

if OPENAI_API_KEY and not LM_CORRECTION_ENABLED:
    LM_CORRECTION_ENABLED = True

# Global speaker model instance
speaker_model = None
lm_client = None
lm_client_init_attempted = False

if PYANNOTE_TOKEN:
    try:
        print("Speaker ID: pyannote token detected; will attempt to load embedding model on first use.")
    except Exception:
        pass
else:
    try:
        print("Speaker ID: no pyannote token found; speaker identification disabled. Set PYANNOTE_TOKEN or tokenHF.txt.")
    except Exception:
        pass

if OPENAI_API_KEY and not LM_CORRECTION_ENABLED:
    LM_CORRECTION_ENABLED = True

audio_queue = queue.Queue()
last_audio_level = 0.0
interim_queue = queue.Queue()
connected_clients = set()
client_prefs = {}
vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
# Initialize speaker model if enabled
if SPEAKER_ID_ENABLED:
    speaker_model = get_speaker_model(threshold=SPEAKER_THRESHOLD, device=device)
    print(f"Speaker ID: enabled with threshold={SPEAKER_THRESHOLD}")
else:
    print("Speaker ID: disabled")
pending_per_speaker = {}
last_sent_per_speaker = {}
recent_messages = []
transcript_buffer = deque(maxlen=1000)
last_interim_per_speaker = {}
last_voiced_ts = time.time()
interim_history_per_speaker = {}
last_emitted_interim_text = {}
stream_display_names = {}

TRANSCRIPT_FH = open(TRANSCRIPT_PATH, "a", encoding="utf-8")
SUMMARY_FH = open(SUMMARY_PATH, "a", encoding="utf-8")


def audio_callback(indata, frames, time_info, status):
    if status:
        pass
    try:
        lvl = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
    except Exception:
        lvl = 0.0
    globals()["last_audio_level"] = lvl
    audio_queue.put(indata.copy())


def start_audio_stream():
    try:
        dev_info = sd.query_devices(DEVICE_ID)
        dev_name = dev_info.get("name", "")
        if ALLOWED_INPUT_DEVICE_SUBSTRINGS:
            if not any(s in dev_name for s in ALLOWED_INPUT_DEVICE_SUBSTRINGS):
                raise RuntimeError(f"Input device not allowed: {dev_name}")
    except Exception:
        pass
    try:
        stream = sd.InputStream(
            device=DEVICE_ID,
            channels=1,
            samplerate=SAMPLE_RATE,
            dtype="float32",
            callback=audio_callback,
        )
        stream.start()
        print(f"Audio stream started (device={DEVICE_ID}, sr={SAMPLE_RATE}).")
        return stream
    except Exception:
        stream = sd.InputStream(channels=1, samplerate=SAMPLE_RATE, dtype="float32", callback=audio_callback)
        stream.start()
        print(f"Audio stream started (default device, sr={SAMPLE_RATE}).")
        return stream


def resolve_speaker_name(stream_id: str, speaker_label: str) -> str:
    """Resolve the display name for a speaker.

    If the frontend has registered a human-readable name for this stream_id,
    return that; otherwise fall back to the diarization label (e.g. "Speaker 1").
    """

    try:
        sid = (stream_id or "").strip()
    except Exception:
        sid = ""
    name = stream_display_names.get(sid)
    if isinstance(name, str) and name.strip():
        resolved = name.strip()
        try:
            print(f"Speaker name resolved: stream_id={sid} -> '{resolved}' (label={speaker_label})")
        except Exception:
            pass
        return resolved

    label = speaker_label or "Speaker"
    if not isinstance(label, str) or not label.strip():
        return "Speaker"
    return label.strip()


def _float_to_int16_pcm(audio: np.ndarray) -> bytes:
    a = np.clip(audio, -1.0, 1.0)
    a = (a * 32767.0).astype(np.int16)
    return a.tobytes()


def _resample_linear(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return audio.astype(np.float32)
    n = int(len(audio) * target_sr / orig_sr)
    if n <= 0:
        return audio.astype(np.float32)
    x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=n, endpoint=False)
    y = np.interp(x_new, x_old, audio.astype(np.float32)).astype(np.float32)
    return y


def apply_noise_suppression(audio: np.ndarray) -> np.ndarray:
    if not USE_RNNOISE:
        return audio
    if rnnoise is None:
        return audio
    try:
        audio = audio.astype(np.float32)
        # RNNoise expects 16-bit PCM frames of 480 samples at 48 kHz (10 ms)
        frame_len = 480
        pcm = _float_to_int16_pcm(audio)
        out_frames = []
        denoiser = rnnoise.RNNoise()
        for i in range(0, len(pcm), frame_len * 2):
            frame = pcm[i : i + frame_len * 2]
            if len(frame) < frame_len * 2:
                break
            denoised = denoiser.process_frame(frame)
            out_frames.append(denoised)
        if not out_frames:
            return audio
        out_pcm = b"".join(out_frames)
        out_int16 = np.frombuffer(out_pcm, dtype=np.int16)
        out_float = (out_int16.astype(np.float32) / 32767.0).astype(np.float32)
        # Trim or pad to original length if needed
        if len(out_float) > len(audio):
            out_float = out_float[: len(audio)]
        elif len(out_float) < len(audio):
            pad = np.zeros(len(audio) - len(out_float), dtype=np.float32)
            out_float = np.concatenate([out_float, pad])
        return out_float
    except Exception:
        return audio


def normalize_audio(audio: np.ndarray, target_rms: float = 0.12, max_gain: float = 10.0) -> np.ndarray:
    x = audio.astype(np.float32, copy=False)
    if x.size == 0:
        return x

    rms_before = float(np.sqrt(np.mean(x ** 2)))
    if rms_before <= 1e-6:
        return x

    gain = target_rms / rms_before
    if gain > max_gain:
        gain = max_gain

    y = x * gain
    y = np.tanh(y)

    try:
        import time as _time  # local alias to avoid polluting module namespace

        if not hasattr(normalize_audio, "_last_log_time"):
            normalize_audio._last_log_time = 0.0  # type: ignore[attr-defined]
        now = _time.time()
        if now - normalize_audio._last_log_time >= 5.0:  # type: ignore[attr-defined]
            normalize_audio._last_log_time = now  # type: ignore[attr-defined]
            rms_after = float(np.sqrt(np.mean(y ** 2)))
            try:
                print(f"normalize_audio: rms_before={rms_before:.4f}, rms_after={rms_after:.4f}, gain={gain:.2f}")
            except Exception:
                pass
    except Exception:
        pass

    return y


def restore_punctuation(text: str) -> str:
    if not text:
        return text
    t = text.strip()
    if not t:
        return t
    if t[-1] not in ".!?":
        t = t + "."
    if t[0].islower():
        t = t[0].upper() + t[1:]
    return t


BLOCKLIST_HALLUCINATIONS = {
    "thank you",
    "thank you very much",
    "thanks",
    "thanks for watching",
    "so",
    "okay",
    "ok",
    "i don't know",
    "home",
    "i'll see you in the next video",
    "we'll see you next time",
    "bye",
    "beep",
    "beep beep",
    "beep beep beep",
    "all right",
    "alright",
    "yeah",
    "yea",
    "oh",
    "ooh",
    "no",
    "ok",
    "okay",
    "um",
    "uh",
    "hmm",
    "trim",
    "i'm done",
    "i should have",
    "i love you",
    "i love it",
    "i love",
    "mm-hmm",
    "mm hmm",
    "mmm",
    "and that's it",
    "you should be fine",
    "you're welcome",
    "see you next time",
}


def is_low_value_transcript(text: str) -> bool:
    """Drop filler / one-word hallucinations that are not real meeting speech."""
    t = (text or "").strip()
    if not t:
        return True
    norm = t.lower().strip(".,!? ")
    words = [w for w in norm.split() if w]
    # Real sentences (3+ words) should always pass to the UI.
    if len(words) >= 3:
        return False
    if is_hallucination(t):
        return True
    filler_one = {
        "yeah", "yea", "yes", "no", "oh", "ooh", "ok", "okay", "um", "uh", "hmm",
        "right", "trim", "done",
    }
    if norm in filler_one:
        return True
    if norm in {
        "all right", "alright", "i'm done", "i should have", "thank you",
        "i love you", "i love it", "i love", "mm-hmm", "mm hmm", "mmm",
        "and that's it", "you should be fine",
    }:
        return True
    if len(words) == 1 and len(norm) < 6:
        return True
    return False


def is_hallucination(text: str) -> bool:
    """Return True only for exact known hallucination phrases (not prefix match)."""

    t = (text or "").lower().strip()
    for ch in ".!,?":
        t = t.replace(ch, "")
    return t in BLOCKLIST_HALLUCINATIONS


def webrtc_vad_voiced_ratio(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> float:
    frame_ms = 30
    frame_len = int(sample_rate * frame_ms / 1000)
    pcm = _float_to_int16_pcm(audio)
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


def get_speaker_label(audio_chunk: np.ndarray):
    """Get speaker label using the SpeakerModel."""
    if not SPEAKER_ID_ENABLED or speaker_model is None:
        return "Speaker"
    
    try:
        return speaker_model.identify(audio_chunk, PYANNOTE_TOKEN)
    except Exception as e:
        print(f"Speaker identification failed: {type(e).__name__}: {e}")
        return "Speaker"


def rnnt_transcribe_chunk(audio_16k: np.ndarray) -> str:
    if rnnt_model is None or rnnt_decoding is None:
        return ""
    try:
        a = audio_16k.astype(np.float32)
        if a.ndim == 2:
            a = a.squeeze(-1)
        if a.ndim == 1:
            a = a[None, :]
        sig = torch.from_numpy(a).to(device)
        length = torch.tensor([sig.shape[-1]], dtype=torch.long, device=device)
        with torch.no_grad():
            processed_audio, processed_audio_len = rnnt_model.preprocessor(
                input_signal=sig, length=length
            )
            hyps = rnnt_decoding(audio_signal=processed_audio, length=processed_audio_len)
            hyps = rnnt_model.decoding.decode_hypothesis(hyps)
        if not hyps:
            return ""
        h0 = hyps[0]
        try:
            text = (h0.text or "").strip()
        except Exception:
            text = str(h0).strip()
        # Debug: log raw RNNT output to understand what the model is producing
        if text:
            try:
                print(f"RNNT raw: '{text}' (len={len(text)})")
            except Exception:
                pass
        return text
    except Exception:
        return ""


def whisper_transcribe_chunk(audio_16k: np.ndarray, language: str) -> str:
    """Transcribe a 16 kHz mono audio chunk with Whisper and log raw output."""
    try:
        a = audio_16k.astype(np.float32)
        if a.ndim == 2:
            a = a.squeeze(-1)
        if a.ndim == 0:
            return ""
        
        # Safety normalization: ensure audio is in [-1, 1]
        max_val = np.max(np.abs(a))
        if max_val > 1.0:
            a = a / max_val
        
        # Debug audio stats
        try:
            print(f"Whisper input: len={len(a)}, max={max_val:.4f}, rms={np.sqrt(np.mean(a**2)):.4f}")
        except Exception:
            pass
            
        lang_arg = language if language else None
        segments, info = whisper_model.transcribe(
            a,
            language=lang_arg or "en",
            beam_size=max(DECODE_BEAM_SIZE, 1),
            best_of=1,
            temperature=0.0,
            condition_on_previous_text=False,
            vad_filter=False,
            word_timestamps=False,
            initial_prompt=WHISPER_INITIAL_PROMPT,
            no_speech_threshold=float(os.getenv("NO_SPEECH_THRESHOLD", "0.65")),
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
        )
        try:
            nsp = float(getattr(info, "no_speech_prob", 0.0) or 0.0)
            if nsp > MAX_NO_SPEECH_PROB:
                print(f"Whisper skip chunk: no_speech_prob={nsp:.2f}")
                return ""
        except Exception:
            pass
        parts = []
        total_segments = 0
        for seg in segments:
            try:
                total_segments += 1
                t = (getattr(seg, "text", "") or "").strip()
                seg_lp = getattr(seg, "avg_logprob", None)
                seg_nsp = getattr(seg, "no_speech_prob", None)
                if seg_lp is not None and seg_lp < MIN_SEGMENT_LOGPROB:
                    print(f"Whisper drop low logprob segment: '{t}' lp={seg_lp:.2f}")
                    continue
                if seg_nsp is not None and seg_nsp > MAX_NO_SPEECH_PROB:
                    print(f"Whisper drop no-speech segment: '{t}' nsp={seg_nsp:.2f}")
                    continue
            except Exception:
                t = str(seg).strip()
            if not t:
                continue
            parts.append(t)
        text = " ".join(parts).strip()
        try:
            print(f"Whisper debug: segments_total={total_segments}, kept={len(parts)}")
        except Exception:
            pass
        if text:
            try:
                print(f"Whisper raw: '{text}' (len={len(text)})")
            except Exception:
                pass
        return text
    except Exception as e:
        try:
            print(f"Whisper error: {type(e).__name__}: {e}")
        except Exception:
            pass
        return ""


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


def write_jsonl_line(fh, obj):
    fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
    fh.flush()


async def broadcast_json(obj):
    if not connected_clients:
        return
    msg = json.dumps(obj, ensure_ascii=False)
    await asyncio.gather(*[ws.send(msg) for ws in list(connected_clients)], return_exceptions=True)


async def broadcast_captions_from_interim(payload):
    """Broadcast per-client caption messages derived from an interim payload.

    Uses each websocket's configured ``translate_to`` language. If a client has
    not set a target language, no caption is sent for that client.
    """

    if not connected_clients:
        return
    if not isinstance(payload, dict):
        return

    text = (payload.get("text") or "").strip()
    if not text:
        return

    try:
        src_lang = (payload.get("source_lang") or WHISPER_DEFAULT_LANGUAGE or "en").lower()
    except Exception:
        src_lang = (WHISPER_DEFAULT_LANGUAGE or "en").lower()

    ts_str = payload.get("timestamp")
    stream_id = payload.get("stream_id", STREAM_ID)
    speaker = payload.get("speaker", "Speaker")

    clients_snapshot = list(connected_clients)
    send_tasks = []

    for ws in clients_snapshot:
        prefs = client_prefs.get(ws) or {}
        target = (prefs.get("translate_to") or "").strip().lower()
        if not target:
            continue

        try:
            if target == src_lang:
                translated = text
            else:
                translator = get_translator(src_lang, target)
                translated = await asyncio.to_thread(translator.translate, text)
        except Exception:
            translated = text

        caption_payload = {
            "type": "caption",
            "stream_id": stream_id,
            "timestamp": ts_str,
            "speaker": speaker,
            "text": translated,
            "original": text,
            "lang": target,
        }
        msg = json.dumps(caption_payload, ensure_ascii=False)
        send_tasks.append(ws.send(msg))

    if send_tasks:
        await asyncio.gather(*send_tasks, return_exceptions=True)


async def handle_client(websocket):
    connected_clients.add(websocket)
    stream_id = STREAM_ID
    lang = WHISPER_DEFAULT_LANGUAGE
    client_prefs[websocket] = {"translate_to": None, "sample_rate": CLIENT_INPUT_SAMPLE_RATE}
    
    # Audio recording for debugging
    raw_audio_buffer = []
    
    try:
        async for message in websocket:
            if isinstance(message, (bytes, bytearray)):
                try:
                    flat = np.frombuffer(message, dtype=np.float32)
                    if flat.size == 0:
                        continue
                    prefs = client_prefs.get(websocket) or {}
                    in_sr = int(prefs.get("sample_rate") or CLIENT_INPUT_SAMPLE_RATE)
                    if in_sr != SAMPLE_RATE:
                        flat = _resample_linear(flat.astype(np.float32), in_sr, SAMPLE_RATE)
                    else:
                        flat = flat.astype(np.float32)
                    audio = flat.reshape(-1, 1)
                    while audio_queue.qsize() > MAX_AUDIO_QUEUE:
                        try:
                            audio_queue.get_nowait()
                        except queue.Empty:
                            break
                    if RECORD_DEBUG_AUDIO:
                        raw_audio_buffer.append(flat.copy())
                    try:
                        globals()["last_audio_level"] = float(
                            np.sqrt(np.mean(flat.astype(np.float32) ** 2))
                        )
                    except Exception:
                        globals()["last_audio_level"] = 0.0
                    audio_queue.put(
                        {
                            "audio": audio,
                            "stream_id": stream_id,
                            "language": lang,
                        }
                    )
                except Exception as exc:
                    try:
                        print(f"Audio ingest error: {type(exc).__name__}: {exc}")
                    except Exception:
                        pass
            else:
                try:
                    data = json.loads(message)
                    if isinstance(data, dict):
                        msg_type = data.get("type")
                        if msg_type == "config":
                            sid = data.get("stream_id")
                            if isinstance(sid, str) and sid.strip():
                                stream_id = sid.strip()
                            lg = data.get("language")
                            if isinstance(lg, str) and lg.strip():
                                lg_clean = lg.strip().lower()
                                if lg_clean not in {"", "auto"}:
                                    lang = lg_clean
                                else:
                                    lang = WHISPER_DEFAULT_LANGUAGE
                            tgt = data.get("translate_to")
                            prefs = client_prefs.get(websocket) or {}
                            if isinstance(tgt, str) and tgt.strip():
                                prefs["translate_to"] = tgt.strip()
                            sr = data.get("sample_rate")
                            if isinstance(sr, (int, float)) and int(sr) > 0:
                                prefs["sample_rate"] = int(sr)
                            client_prefs[websocket] = prefs
                        elif msg_type == "register_user":
                            sid = data.get("stream_id") or stream_id
                            name = data.get("name")
                            if isinstance(sid, str) and sid.strip() and isinstance(name, str) and name.strip():
                                sid_clean = sid.strip()
                                name_clean = name.strip()
                                stream_display_names[sid_clean] = name_clean
                                try:
                                    print(f"Registered user: stream_id={sid_clean} name='{name_clean}'")
                                except Exception:
                                    pass
                                await broadcast_json({
                                    "type": "participant",
                                    "stream_id": sid_clean,
                                    "speaker": name_clean,
                                })
                        elif msg_type == "chat":
                            sender = (data.get("sender") or "").strip()
                            if not sender:
                                sender = stream_display_names.get(stream_id, "User")
                            body = (data.get("text") or "").strip()
                            image_data = data.get("image")
                            if body or image_data:
                                chat_payload = {
                                    "type": "chat",
                                    "stream_id": stream_id,
                                    "sender": sender,
                                    "text": body,
                                    "image": image_data,
                                    "timestamp": time.strftime("%H:%M:%S"),
                                }
                                await broadcast_json(chat_payload)
                except Exception:
                    pass
    except websockets.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        client_prefs.pop(websocket, None)
        
        # Save recorded raw audio for debugging
        if RECORD_DEBUG_AUDIO and raw_audio_buffer:
            try:
                raw_audio = np.concatenate(raw_audio_buffer)
                timestamp = datetime.now().strftime("%H%M%S")
                raw_file = DEBUG_AUDIO_DIR / f"raw_input_{timestamp}.wav"
                
                # Save as 16kHz mono WAV
                with wave.open(str(raw_file), 'wb') as wf:
                    wf.setnchannels(1)  # mono
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(16000)  # 16kHz
                    # Convert float32 to int16
                    audio_int16 = (raw_audio * 32767).astype(np.int16)
                    wf.writeframes(audio_int16.tobytes())
                
                print(f"DEBUG: Saved raw audio to {raw_file}")
            except Exception as e:
                print(f"DEBUG: Failed to save raw audio: {e}")


def transcribe_worker():
    buffer = np.zeros((0, 1), dtype=np.float32)
    last_processed_time = 0.0
    min_process_interval = 0.05
    max_buf = int(SAMPLE_RATE * max(CHUNK_DURATION + 0.5, 1.5))
    while True:
        while audio_queue.qsize() > MAX_AUDIO_QUEUE:
            try:
                audio_queue.get_nowait()
            except queue.Empty:
                break
        item = audio_queue.get()
        if isinstance(item, dict):
            data = item.get("audio")
            stream_id = item.get("stream_id", STREAM_ID)
            lang = item.get("language", WHISPER_DEFAULT_LANGUAGE)
        else:
            # backward compatibility: raw numpy array
            data = item
            stream_id = STREAM_ID
            lang = WHISPER_DEFAULT_LANGUAGE
        buffer = np.concatenate((buffer, data), axis=0)
        if len(buffer) > max_buf:
            buffer = buffer[-max_buf:]

        while len(buffer) >= CHUNK_SIZE:
            now = time.time()
            if (now - last_processed_time) < min_process_interval:
                break
            last_processed_time = now

            chunk_arr = buffer[:CHUNK_SIZE].squeeze().copy()
            if len(chunk_arr) < CHUNK_SIZE:
                break

            norm = normalize_audio(chunk_arr)
            pre = apply_noise_suppression(norm)
            voiced_ratio = webrtc_vad_voiced_ratio(pre, SAMPLE_RATE)
            rms = float(np.sqrt(np.mean(pre.astype(np.float32) ** 2)))

            gate_ok = True
            if np.allclose(pre, 0, atol=1e-4):
                gate_ok = False
            elif (rms < RMS_MIN_LEVEL) and (voiced_ratio < VAD_MIN_VOICED_RATIO):
                if int(time.time()) % 5 == 0:
                    print(
                        f"Gate filtered: rms={rms:.4f} < {RMS_MIN_LEVEL:.4f} "
                        f"and voiced={voiced_ratio:.2f} < {VAD_MIN_VOICED_RATIO:.2f}"
                    )
                gate_ok = False

            if not gate_ok:
                buffer = buffer[CHUNK_ADVANCE:]
                continue

            try:
                try:
                    print(f"ASR chunk: voiced={voiced_ratio:.2f}, rms={rms:.4f}, n={len(pre)}")
                except Exception:
                    pass

                # Optional time-compression before Whisper (default 1.0 = disabled)
                eff_sr = SAMPLE_RATE
                if WHISPER_SPEEDUP_FACTOR > 0.0 and abs(WHISPER_SPEEDUP_FACTOR - 1.0) > 1e-3:
                    eff_sr = int(SAMPLE_RATE * WHISPER_SPEEDUP_FACTOR)
                resampled = _resample_linear(pre, eff_sr, TARGET_SR)

                # Pre-ASR diagnostics: duration and save exact Whisper input chunk
                try:
                    dur_sec = len(resampled) / float(TARGET_SR) if TARGET_SR > 0 else 0.0
                    print(f"Whisper chunk: samples={len(resampled)}, dur={dur_sec:.3f}s")
                except Exception:
                    pass

                processed_file = None
                if RECORD_DEBUG_AUDIO:
                    try:
                        timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]  # milliseconds
                        processed_file = DEBUG_AUDIO_DIR / f"whisper_input_{timestamp}.wav"

                        with wave.open(str(processed_file), 'wb') as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(16000)
                            audio_int16 = (resampled * 32767).astype(np.int16)
                            wf.writeframes(audio_int16.tobytes())

                        try:
                            print(f"DEBUG: Saved Whisper input chunk to {processed_file} (dur={dur_sec:.3f}s)")
                        except Exception:
                            pass
                    except Exception:
                        pass

                text = whisper_transcribe_chunk(resampled, lang)

                # Block known hallucinated / YouTube-outro style phrases at the
                # earliest stage so they never appear as interim or final text.
                if is_low_value_transcript(text):
                    try:
                        print("Blocked low-value ASR:", text)
                    except Exception:
                        pass
                    text = ""

                globals()["last_voiced_ts"] = time.time()
                if PUNCTUATION_ENABLED:
                    text = restore_punctuation(text)
                if not text:
                    buffer = buffer[CHUNK_ADVANCE:]
                    continue

                speaker_label = "Speaker"
                if SPEAKER_ID_ENABLED:
                    speaker_label = get_speaker_label(chunk_arr)
                display_speaker = resolve_speaker_name(stream_id, speaker_label)

                now_ts = time.time()
                prev = pending_per_speaker.get(speaker_label)
                if prev:
                    prev_text = prev.get("text", "")
                    sim = difflib.SequenceMatcher(None, prev_text, text).ratio()
                    stable = prev.get("stable", 0)
                    if sim >= STABLE_SIMILARITY_FINAL:
                        stable += 1
                    else:
                        stable = 0
                    pending_per_speaker[speaker_label] = {
                        "text": text,
                        "ts": now_ts,
                        "stable": stable,
                        "stream_id": stream_id,
                    }
                else:
                    pending_per_speaker[speaker_label] = {
                        "text": text,
                        "ts": now_ts,
                        "stable": 0,
                        "stream_id": stream_id,
                    }

                if INTERIM_ENABLED:
                    now_time = time.time()
                    prev_i = last_interim_per_speaker.get(speaker_label)
                    allow_emit = True
                    if prev_i:
                        if (now_time - prev_i["ts"]) < INTERIM_MIN_INTERVAL:
                            allow_emit = False
                        else:
                            prev_text = prev_i.get("text", "")
                            try:
                                sim = difflib.SequenceMatcher(None, prev_text, text).ratio()
                            except Exception:
                                sim = 1.0 if prev_text == text else 0.0
                            if sim >= INTERIM_SIMILARITY_SKIP:
                                allow_emit = False
                    if allow_emit and not is_low_value_transcript(text):
                        ts_str = time.strftime("%H:%M:%S")
                        interim_payload = {
                            "type": "interim",
                            "stream_id": stream_id,
                            "timestamp": ts_str,
                            "speaker": display_speaker,
                            "text": text,
                            "source_lang": lang,
                        }
                        last_interim_per_speaker[speaker_label] = {"text": text, "ts": now_time}
                        try:
                            interim_queue.put(interim_payload)
                        except Exception:
                            pass
            except Exception:
                pass

            buffer = buffer[CHUNK_ADVANCE:]


async def pending_flusher():
    while True:
        now_ts = time.time()
        to_send = []
        silence_exceeded = (now_ts - last_voiced_ts) >= SILENCE_FINALIZE_SEC
        for spk, entry in list(pending_per_speaker.items()):
            age = now_ts - entry["ts"]
            stable = entry.get("stable", 0)
            should_finalize = False
            finalize_due_to_silence = False
            if age >= DEBOUNCE_SECONDS and stable >= STABLE_ROUNDS_REQUIRED:
                should_finalize = True
            elif silence_exceeded and age >= 0.3:
                should_finalize = True
                finalize_due_to_silence = True
            if should_finalize:
                text = entry["text"].strip()
                sid = entry.get("stream_id", STREAM_ID)
                pending_per_speaker.pop(spk, None)
                if len(text) < 2:
                    continue
                if sum(ch.isalpha() for ch in text) < MIN_ALPHA_FINAL:
                    continue

                final_text = text
                try:
                    li_entry = last_interim_per_speaker.get(spk)
                    if li_entry:
                        li_text = (li_entry.get("text") or "").strip()
                        if len(li_text) > len(final_text):
                            final_text = li_text
                except Exception:
                    pass

                last = last_sent_per_speaker.get(spk)
                if last:
                    last_text, _last_time = last
                    if final_text.strip().lower() == last_text.strip().lower():
                        continue
                    try:
                        sim = difflib.SequenceMatcher(
                            None, last_text.strip().lower(), final_text.strip().lower()
                        ).ratio()
                        if sim >= 0.92:
                            continue
                    except Exception:
                        pass

                final_text = final_text.strip()
                if not final_text:
                    continue

                if finalize_due_to_silence and is_low_value_transcript(final_text):
                    try:
                        print("Blocked silence hallucination:", final_text)
                    except Exception:
                        pass
                    continue

                to_send.append((spk, final_text, sid))
        for spk, text, stream_id in to_send:
            ts_str = time.strftime("%H:%M:%S")
            alpha_letters = sum(ch.isalpha() for ch in text)
            if alpha_letters < MIN_ALPHA_FINAL:
                continue
            if is_low_value_transcript(text):
                try:
                    print("Blocked low-value final:", text)
                except Exception:
                    pass
                continue
            words = [w for w in text.split() if w.strip()]
            if len(words) < MIN_WORDS_FINAL:
                continue
            corrected_text = text
            try:
                nlp_res = process_interim_text(text, "", is_final=True)
                corrected_text = (nlp_res.get("text") or text).strip() or text
            except Exception:
                corrected_text = text
            if not corrected_text.strip():
                corrected_text = text
            if LM_CORRECTION_ENABLED and len(corrected_text) >= 10:
                try:
                    corrected_text = await lm_correct_text(corrected_text)
                except Exception:
                    pass
            display_speaker = resolve_speaker_name(stream_id, spk)
            formatted = format_segment(display_speaker, corrected_text, ts_str)
            payload = {
                "type": "transcript",
                "stream_id": stream_id,
                "timestamp": ts_str,
                "speaker": display_speaker,
                "text": corrected_text,
                "formatted": formatted,
            }
            last_sent_per_speaker[spk] = (text, time.time())
            add_recent_message(text)
            entry_payload = dict(payload)
            entry_payload["_ts"] = time.time()
            transcript_buffer.append(entry_payload)
            print(f"Transcribed: {text}")
            write_jsonl_line(TRANSCRIPT_FH, payload)
            await broadcast_json(payload)
        await asyncio.sleep(0.12)


def build_summarizer():
    client = None
    local = None
    try:
        from openai import OpenAI
        if OPENAI_API_KEY:
            client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        client = None
    return client, None


def _rule_based_summary(text: str) -> str:
    """Fast fallback when OpenAI is unavailable."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""
    unique = []
    for ln in lines:
        if not unique or difflib.SequenceMatcher(None, unique[-1], ln).ratio() < 0.85:
            unique.append(ln)
    bullets = unique[-12:]
    return "Key points (last 5 min):\n" + "\n".join(f"- {b}" for b in bullets)


async def _run_summary(client, local, text: str) -> str | None:
    text = (text or "").strip()
    if not text:
        return None
    text = text[-8000:]
    summary = None
    if client is not None:
        try:
            prompt = (
                "Summarize this meeting segment (Hindi/English/Hinglish). "
                "Return: (1) Main topics, (2) Key decisions, (3) Action items. "
                "Be concise, accurate, use the same language mix as the transcript.\n\n"
                f"{text}"
            )
            resp = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model=SUMMARY_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                )
            )
            summary = resp.choices[0].message.content
        except Exception as e:
            try:
                print(f"Summarizer OpenAI error: {type(e).__name__}: {e}")
            except Exception:
                pass
            summary = None
    if summary is None:
        summary = _rule_based_summary(text)
    if summary is None and local is not None:
        try:
            out = await asyncio.to_thread(
                lambda: local(text, max_length=200, min_length=60, do_sample=False)
            )
            summary = out[0]["summary_text"]
        except Exception:
            summary = None
    return summary


async def persist_summary_to_db(payload: dict) -> None:
    """Save rolling summary to PostgreSQL via Auth API (admin dashboard)."""
    if not AUTH_API_URL or not (payload.get("text") or "").strip():
        return
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                f"{AUTH_API_URL.rstrip('/')}/api/internal/summaries",
                headers={"X-Internal-Key": INTERNAL_API_KEY},
                json={
                    "session_key": SESSION_START,
                    "timestamp": payload.get("timestamp", ""),
                    "text": payload.get("text", ""),
                    "interval_seconds": SUMMARY_INTERVAL,
                    "title": f"Meeting {SESSION_START}",
                },
            )
            if resp.status_code >= 400:
                print(f"Summary DB persist HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        print(f"Summary DB persist error: {type(exc).__name__}: {exc}")


async def summarize_loop():
    client, local = build_summarizer()
    last_window_start = time.time()
    if client:
        print(f"Summarizer: OpenAI active, every {SUMMARY_INTERVAL}s window.")
    else:
        print(f"Summarizer: rule-based fallback, every {SUMMARY_INTERVAL}s window.")
    try:
        while True:
            await asyncio.sleep(SUMMARY_INTERVAL)
            now_ts = time.time()
            entries = list(transcript_buffer)
            window = [
                r
                for r in entries
                if r.get("_ts", 0.0) >= (now_ts - SUMMARY_WINDOW) and r.get("_ts", 0.0) <= now_ts
            ]
            last_window_start = now_ts
            if not window:
                continue
            lines = []
            for r in window:
                t = (r.get("text") or "").strip()
                if not t or r.get("type") == "summary":
                    continue
                sp = r.get("speaker", "?")
                line = f"({sp}) {t}"
                if lines and difflib.SequenceMatcher(None, lines[-1], line).ratio() > 0.9:
                    lines[-1] = line
                else:
                    lines.append(line)
            text = "\n".join(lines)
            if not text.strip():
                continue
            summary = await _run_summary(client, local, text)
            if summary:
                ts_str = time.strftime("%H:%M:%S")
                payload = {"type": "summary", "timestamp": ts_str, "text": summary}
                write_jsonl_line(SUMMARY_FH, payload)
                await broadcast_json(payload)
                await persist_summary_to_db(payload)
    except asyncio.CancelledError:
        # On shutdown / meeting end, emit a final overall summary for the session.
        try:
            entries = list(transcript_buffer)
            if entries:
                text = "\n".join(
                    [
                        f"({r.get('speaker', '?')}) {r.get('text', '')}"
                        for r in entries
                        if r.get("text")
                    ]
                )
                summary = await _run_summary(client, local, text)
                if summary:
                    ts_str = time.strftime("%H:%M:%S")
                    payload = {
                        "type": "summary_final",
                        "timestamp": ts_str,
                        "text": summary,
                    }
                    write_jsonl_line(SUMMARY_FH, payload)
                    await broadcast_json(payload)
                    await persist_summary_to_db(payload)
        finally:
            raise


def get_lm_client():
    global lm_client, lm_client_init_attempted
    if lm_client_init_attempted:
        return lm_client
    lm_client_init_attempted = True
    try:
        from openai import OpenAI
        if OPENAI_API_KEY:
            lm_client = OpenAI(api_key=OPENAI_API_KEY)
        else:
            lm_client = None
    except Exception:
        lm_client = None
    return lm_client


async def lm_correct_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return raw_text
    try:
        history = list(transcript_buffer)[-10:]
        context_lines = [f"({r['speaker']}) {r['text']}" for r in history]
        context = "\n".join(context_lines)
    except Exception:
        context = ""

    # First, try external NLP microservice if configured
    if NLP_SERVICE_URL:
        try:
            url = NLP_SERVICE_URL.rstrip("/") + "/correct"
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(url, json={"text": text, "context": context})
            if resp.status_code == 200:
                data = resp.json() or {}
                corrected = (data.get("corrected_text") or "").strip()
                if corrected:
                    return corrected
        except Exception:
            pass

    # Fallback to local OpenAI-based correction if available
    client = get_lm_client()
    if client is None:
        return raw_text
    try:
        prompt_parts = []
        if context:
            prompt_parts.append("Previous conversation (for context):\n" + context + "\n\n")
        prompt_parts.append("Raw ASR text (possibly noisy):\n" + text + "\n\n")
        prompt_parts.append("Return a corrected, well-punctuated version of the raw ASR text as a single line, preserving meaning and keeping it concise.")
        prompt = "".join(prompt_parts)
        def _do_call():
            return client.chat.completions.create(
                model=LM_CORRECTION_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
        resp = await asyncio.to_thread(_do_call)
        out = resp.choices[0].message.content or ""
        out = out.strip()
        if out:
            return out
        return raw_text
    except Exception:
        return raw_text


async def start_websocket_server():
    server = await websockets.serve(handle_client, WEBSOCKET_HOST, WEBSOCKET_PORT)
    print(f"WebSocket server listening on ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    return server


async def run_async():
    server = await start_websocket_server()
    summarizer_task = asyncio.create_task(summarize_loop())
    flusher_task = asyncio.create_task(pending_flusher())
    async def interim_broadcaster():
        while True:
            try:
                sent = 0
                while True:
                    try:
                        payload = interim_queue.get_nowait()
                    except queue.Empty:
                        break
                    await broadcast_json(payload)
                    try:
                        if isinstance(payload, dict) and payload.get("type") == "interim":
                            await broadcast_captions_from_interim(payload)
                    except Exception:
                        pass
                    sent += 1
                await asyncio.sleep(0.02 if sent else 0.08)
            except Exception:
                await asyncio.sleep(0.2)
    interim_task = asyncio.create_task(interim_broadcaster())
    async def level_monitor():
        while True:
            try:
                print(f"Audio RMS={last_audio_level:.4f} | queue={audio_queue.qsize()} | pending={len(pending_per_speaker)}")
            except Exception:
                pass
            await asyncio.sleep(2.0)
    monitor_task = asyncio.create_task(level_monitor())
    print(
        f"Backend ready: model={WHISPER_MODEL_NAME}, chunk={CHUNK_DURATION}s, "
        f"summaries every {SUMMARY_INTERVAL}s, finals enabled."
    )
    try:
        await asyncio.Future()
    finally:
        summarizer_task.cancel()
        flusher_task.cancel()
        interim_task.cancel()
        monitor_task.cancel()
        server.close()
        await server.wait_closed()


def main():
    stream = None
    if USE_LOCAL_MIC:
        stream = start_audio_stream()
        print("Mic stream started (Ctrl+C to stop).")
    t = threading.Thread(target=transcribe_worker, daemon=True)
    t.start()
    try:
        asyncio.run(run_async())
    except KeyboardInterrupt:
        pass
    finally:
        try:
            try:
                if stream is not None:
                    stream.stop()
                    stream.close()
            except Exception:
                pass
            TRANSCRIPT_FH.close()
            SUMMARY_FH.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
