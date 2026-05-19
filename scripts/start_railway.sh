#!/bin/sh
set -e

export USE_LOCAL_MIC="${USE_LOCAL_MIC:-False}"
export SPEAKER_ID_ENABLED="${SPEAKER_ID_ENABLED:-False}"
export WHISPER_MODEL="${WHISPER_MODEL:-base.en}"
export WHISPER_LANGUAGE="${WHISPER_LANGUAGE:-en}"
export CHUNK_DURATION="${CHUNK_DURATION:-2.5}"
export INGEST_SPEEDUP_FACTOR="${INGEST_SPEEDUP_FACTOR:-1.0}"
export NLP_SERVICE_URL="${NLP_SERVICE_URL:-http://127.0.0.1:8100}"
export WEBSOCKET_HOST="${WEBSOCKET_HOST:-0.0.0.0}"

# Railway public port (fallback 8765 for local docker test)
if [ -n "$PORT" ]; then
  export WEBSOCKET_PORT="$PORT"
else
  export WEBSOCKET_PORT="${WEBSOCKET_PORT:-8765}"
fi

echo "Starting NLP service on 8100..."
python nlp_service.py &
NLP_PID=$!

sleep 2

if [ "${ENABLE_WEBRTC_INGEST:-False}" = "True" ]; then
  export ASR_WS_URL="ws://127.0.0.1:${WEBSOCKET_PORT}"
  echo "Starting WebRTC ingest on 8081 (internal)..."
  python webrtc_ingest.py &
fi

echo "Starting ASR WebSocket on port ${WEBSOCKET_PORT}..."
exec python realtime_transcriber.py
