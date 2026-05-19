# Start backend + WebRTC ingest + frontend (run from project root)
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommandPath
Set-Location $ProjectDir

. (Join-Path $ProjectDir "scripts\load_dotenv.ps1")

$py = Join-Path $ProjectDir "venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Creating venv..."
    python -m venv venv
    & ".\venv\Scripts\pip.exe" install -r requirements.txt
}

$env:USE_LOCAL_MIC = "False"
$env:WHISPER_MODEL = if ($env:WHISPER_MODEL) { $env:WHISPER_MODEL } else { "base.en" }
$env:INGEST_SPEEDUP_FACTOR = if ($env:INGEST_SPEEDUP_FACTOR) { $env:INGEST_SPEEDUP_FACTOR } else { "1.0" }
$env:CHUNK_DURATION = if ($env:CHUNK_DURATION) { $env:CHUNK_DURATION } else { "2.5" }
$env:RMS_MIN_LEVEL = if ($env:RMS_MIN_LEVEL) { $env:RMS_MIN_LEVEL } else { "0.00025" }
$env:VAD_MIN_VOICED_RATIO = if ($env:VAD_MIN_VOICED_RATIO) { $env:VAD_MIN_VOICED_RATIO } else { "0.06" }
$env:WHISPER_LANGUAGE = if ($env:WHISPER_LANGUAGE) { $env:WHISPER_LANGUAGE } else { "en" }
$env:SUMMARY_INTERVAL = if ($env:SUMMARY_INTERVAL) { $env:SUMMARY_INTERVAL } else { "90" }
$env:SUMMARY_WINDOW = if ($env:SUMMARY_WINDOW) { $env:SUMMARY_WINDOW } else { "90" }
$env:LM_CORRECTION_ENABLED = if ($env:LM_CORRECTION_ENABLED) { $env:LM_CORRECTION_ENABLED } else { "False" }
$env:RECORD_DEBUG_AUDIO = "False"

Write-Host "Starting NLP service (http://localhost:8100)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectDir'; & '$py' nlp_service.py"

Start-Sleep -Seconds 2

Write-Host "Starting ASR backend (ws://localhost:8765)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectDir'; `$env:USE_LOCAL_MIC='False'; `$env:WHISPER_MODEL='$($env:WHISPER_MODEL)'; `$env:CHUNK_DURATION='$($env:CHUNK_DURATION)'; `$env:INGEST_SPEEDUP_FACTOR='1.0'; `$env:WHISPER_LANGUAGE='$($env:WHISPER_LANGUAGE)'; `$env:SUMMARY_INTERVAL='$($env:SUMMARY_INTERVAL)'; `$env:LM_CORRECTION_ENABLED='$($env:LM_CORRECTION_ENABLED)'; `$env:NLP_SERVICE_URL='http://localhost:8100'; & '$py' realtime_transcriber.py"

Start-Sleep -Seconds 2

Write-Host "Starting WebRTC ingest (http://localhost:8081)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectDir'; `$env:INGEST_SPEEDUP_FACTOR='1.0'; & '$py' webrtc_ingest.py"

Start-Sleep -Seconds 1

Write-Host "Starting frontend (http://localhost:3000)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectDir\frontend_dashboard'; npm run dev"

Write-Host ""
Write-Host "Open http://localhost:3000 — Connect, Allow Mic, speak."
Write-Host "Use Headphones slider to hear yourself in earbuds."
