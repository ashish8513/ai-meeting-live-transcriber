import io
from typing import Optional

import numpy as np
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import soundfile as sf

# Reuse existing model and helpers from realtime_transcriber
from realtime_transcriber import whisper_model, _resample_linear, TARGET_SR

app = FastAPI(title="ASR Service", version="1.0.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/transcribe-file")
async def transcribe_file(file: UploadFile = File(...), language: Optional[str] = None) -> JSONResponse:
    """Transcribe a full audio file (non-real-time).

    - Accepts common audio formats supported by soundfile/ffmpeg (e.g. WAV, FLAC, OGG).
    - Returns a single text string for the whole file.
    """
    data = await file.read()
    if not data:
        return JSONResponse({"error": "empty file"}, status_code=400)

    try:
        # Decode audio to float32 PCM using soundfile
        audio_io = io.BytesIO(data)
        audio, sr = sf.read(audio_io, dtype="float32")
        if audio.ndim > 1:
            # convert to mono
            audio = np.mean(audio, axis=1).astype("float32")
    except Exception:
        return JSONResponse({"error": "failed to decode audio"}, status_code=400)

    # Resample to TARGET_SR used by the realtime pipeline
    if sr != TARGET_SR:
        audio = _resample_linear(audio, sr, TARGET_SR)

    # Run Whisper once over the full audio
    lang = language or "en"
    segments, _ = whisper_model.transcribe(
        audio,
        language=lang,
        beam_size=5,
        temperature=0.0,
        vad_filter=False,
        condition_on_previous_text=False,
    )

    parts = []
    for seg in segments:
        try:
            t = (seg.text or "").strip()
        except Exception:
            t = ""
        if t:
            parts.append(t)
    text = " ".join(parts).strip()

    return JSONResponse({"text": text, "language": lang})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
