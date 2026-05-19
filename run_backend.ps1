$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

# Load secrets from .env (gitignored) — copy .env.example to .env first
. (Join-Path $ProjectDir "scripts\load_dotenv.ps1")

# Optional: activate local venv if present
$venvActivate = Join-Path $ProjectDir "venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
}

# =========================
# NLP service configuration
# =========================

if (-not $env:NLP_LM_MODEL) { $env:NLP_LM_MODEL = "gpt-4o-mini" }
# $env:NLP_SERVICE_HOST = "0.0.0.0"
# $env:NLP_SERVICE_PORT = "8100"

# URL that the ASR backend will use to call the NLP service
$env:NLP_SERVICE_URL  = "http://localhost:8100"

# =========================
# ASR backend configuration
# =========================

# Use ONLY WebRTC/ingest audio (no local mic)
$env:USE_LOCAL_MIC          = "False"

# RNNT ONNX model paths (INT8)
$env:RNNT_ONNX_ENCODER      = "encoder-rnnt_conformer_small_int8.onnx"
$env:RNNT_ONNX_DECODER      = "decoder_joint-rnnt_conformer_small_int8.onnx"
$env:RNNT_MAX_SYMBOLS_PER_STEP = "5"

# Latency / sensitivity tuning (optional, tweak as needed)
# $env:VAD_MIN_VOICED_RATIO   = "0.05"    # balanced: not too strict, filters silence (was 0.00)
# $env:VAD_AGGRESSIVENESS     = "1"       # moderate filtering (was 0, range 0-3)
# $env:RMS_MIN_LEVEL          = "0.002"   # reasonable volume threshold (was 0.0001)
# $env:INTERIM_MIN_INTERVAL   = "0.15"    # faster interim updates
# $env:SILENCE_FINALIZE_SEC   = "1.0"     # slightly quicker finalization
# $env:CHUNK_DURATION       = "1.2"   # a bit more context per RNNT call
# $env:OVERLAP_DURATION     = "0.3"

# Threading for ONNX / BLAS (tune for your CPU cores)
$env:OMP_NUM_THREADS        = "4"
$env:OPENBLAS_NUM_THREADS   = "4"
$env:MKL_NUM_THREADS        = "4"
$env:NUMEXPR_NUM_THREADS    = "4"
# Enable RNNoise denoiser and debug audio recording for testing
$env:USE_RNNOISE            = "False"
$env:RECORD_DEBUG_AUDIO     = "True"
# $env:WHISPER_SPEEDUP_FACTOR = "2.5"

# =========================
# WebRTC ingest configuration
# =========================

# Where ingest should send 20ms frames (RNNT backend WebSocket)
$env:ASR_WS_URL             = "ws://localhost:8765"

# =========================
# Start services
# =========================

# 1) NLP microservice (FastAPI)
# Start-Process powershell `
#   -WorkingDirectory "C:\Users\Ai Intern\Desktop\ai" `
#   -ArgumentList "python nlp_service.py"

# 2) RNNT ASR backend (WebSocket server on ws://0.0.0.0:8765)
Start-Process powershell `
  -WorkingDirectory $ProjectDir `
  -ArgumentList "python realtime_transcriber.py"

# 3) WebRTC ingest (HTTP /offer on http://0.0.0.0:8081)
Start-Process powershell `
  -WorkingDirectory $ProjectDir `
  -ArgumentList "python webrtc_ingest.py"

# 4) (Optional) Frontend dev server
# Start-Process powershell `
#   -WorkingDirectory (Join-Path $ProjectDir "frontend_dashboard") `
#   -ArgumentList "npm run dev"


#.\run_backend.ps1
#ipconfig | findstr "IPv4"