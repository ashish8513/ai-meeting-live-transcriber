import asyncio
import logging
import os
import json
import uuid

import aiohttp_cors
import numpy as np
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
import websockets

pcs = set()
TARGET_SR = 16000
# Audacity-derived tuning: effective ~2.0x speed-up (Change Speed 1.946 + Tempo +30.986%)
# Must be 1.0 for correct real-time transcription (2.0 corrupts speech / causes hallucinations)
INGEST_SPEEDUP_FACTOR = float(os.getenv("INGEST_SPEEDUP_FACTOR", "1.0"))
FRAME_MS = 20
FRAME_SIZE = int(TARGET_SR * FRAME_MS / 1000)
ASR_WS_URL = os.getenv("ASR_WS_URL", "ws://localhost:8765")


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


async def offer(request: web.Request) -> web.Response:
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    session_id = str(params.get("session_id") or params.get("stream_id") or uuid.uuid4())

    pc = RTCPeerConnection()
    pcs.add(pc)
    logging.info("Created RTCPeerConnection for session %s", session_id)

    @pc.on("track")
    async def on_track(track):  # type: ignore[no-redef]
        logging.info("Track %s received for session %s", track.kind, session_id)
        if track.kind != "audio":
            return

        buf = np.zeros((0,), dtype=np.float32)

        try:
            async with websockets.connect(ASR_WS_URL) as ws:
                cfg = {
                    "type": "config",
                    "stream_id": session_id,
                    "language": "en",
                    "sample_rate": TARGET_SR,
                }
                await ws.send(json.dumps(cfg))

                while True:
                    frame = await track.recv()
                    # Convert incoming frame to numpy and ensure mono float32 audio
                    pcm = frame.to_ndarray()
                    if pcm.ndim == 2:
                        mono = pcm.mean(axis=0)
                    else:
                        mono = pcm
                    mono = mono.astype(np.float32)
                    # Standard WebRTC normalization: int16 -> float32 in [-1, 1]
                    # If incoming is float, assume it's already close to [-1, 1], but check scale
                    max_val = float(np.max(np.abs(mono))) if mono.size > 0 else 0.0
                    # If values are large (like int16 range), normalize
                    if max_val > 1.0:
                        audio = (mono / 32768.0).astype(np.float32)
                    else:
                        audio = mono

                    # Boost quiet mic levels so ASR gate/Whisper receive usable signal
                    rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2))) if audio.size else 0.0
                    if 1e-6 < rms < 0.04:
                        gain = min(0.06 / rms, 12.0)
                        audio = np.clip(audio * gain, -1.0, 1.0).astype(np.float32)

                    # Apply ingest speed-up factor before resampling, so timing/pitch are corrected at source
                    eff_sr = frame.sample_rate
                    if INGEST_SPEEDUP_FACTOR > 0.0:
                        eff_sr = int(frame.sample_rate * INGEST_SPEEDUP_FACTOR)

                    resampled = _resample_linear(audio, eff_sr, TARGET_SR)
                    buf = np.concatenate((buf, resampled))
                    while len(buf) >= FRAME_SIZE:
                        chunk = buf[:FRAME_SIZE]
                        buf = buf[FRAME_SIZE:]
                        await ws.send(chunk.astype(np.float32).tobytes())
        except Exception as exc:
            logging.info("Audio track for session %s ended: %s", session_id, exc)

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.json_response({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})


async def on_shutdown(app: web.Application) -> None:
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    app = web.Application()

    cors = aiohttp_cors.setup(
        app,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        },
    )

    resource = cors.add(app.router.add_resource("/offer"))
    cors.add(resource.add_route("POST", offer))

    app.on_shutdown.append(on_shutdown)

    web.run_app(app, host="0.0.0.0", port=8081)


if __name__ == "__main__":
    main()

