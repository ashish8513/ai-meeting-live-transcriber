# Start full MeetScribe stack (Postgres + Auth API + ASR + Frontend)
$ProjectDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $ProjectDir

. (Join-Path $ProjectDir "scripts\load_dotenv.ps1")

$py = Join-Path $ProjectDir "venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Creating venv..."
    python -m venv venv
    & ".\venv\Scripts\pip.exe" install -r requirements.txt
    & ".\venv\Scripts\pip.exe" install -r requirements-auth.txt
}

$env:USE_LOCAL_MIC = "False"
$env:WHISPER_MODEL = if ($env:WHISPER_MODEL) { $env:WHISPER_MODEL } else { "base.en" }
$env:INGEST_SPEEDUP_FACTOR = if ($env:INGEST_SPEEDUP_FACTOR) { $env:INGEST_SPEEDUP_FACTOR } else { "1.0" }
$env:CHUNK_DURATION = if ($env:CHUNK_DURATION) { $env:CHUNK_DURATION } else { "2.5" }
$env:WHISPER_LANGUAGE = if ($env:WHISPER_LANGUAGE) { $env:WHISPER_LANGUAGE } else { "en" }
$env:SUMMARY_INTERVAL = if ($env:SUMMARY_INTERVAL) { $env:SUMMARY_INTERVAL } else { "5" }
$env:SUMMARY_WINDOW = if ($env:SUMMARY_WINDOW) { $env:SUMMARY_WINDOW } else { "5" }
$env:AUTH_API_URL = if ($env:AUTH_API_URL) { $env:AUTH_API_URL } else { "http://localhost:8200" }
$env:INTERNAL_API_KEY = if ($env:INTERNAL_API_KEY) { $env:INTERNAL_API_KEY } else { "dev-internal-key-change-me" }
if (-not $env:DATABASE_URL) { $env:DATABASE_URL = "sqlite:///./data/meetscribe.db" }
$env:LM_CORRECTION_ENABLED = if ($env:LM_CORRECTION_ENABLED) { $env:LM_CORRECTION_ENABLED } else { "False" }
$env:RECORD_DEBUG_AUDIO = "False"
$env:RMS_MIN_LEVEL = if ($env:RMS_MIN_LEVEL) { $env:RMS_MIN_LEVEL } else { "0.0001" }
$env:VAD_MIN_VOICED_RATIO = if ($env:VAD_MIN_VOICED_RATIO) { $env:VAD_MIN_VOICED_RATIO } else { "0.04" }
$env:MIN_SEGMENT_LOGPROB = if ($env:MIN_SEGMENT_LOGPROB) { $env:MIN_SEGMENT_LOGPROB } else { "-1.25" }

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "Starting PostgreSQL (docker compose)..."
    docker compose up -d postgres 2>$null
    Start-Sleep -Seconds 4
}

$authListen = Get-NetTCPConnection -LocalPort 8200 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($authListen) {
    Stop-Process -Id $authListen.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Host "Stopped old Auth API on port 8200"
}
Write-Host "Starting Auth API (http://localhost:8200)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectDir'; `$env:DATABASE_URL='$($env:DATABASE_URL)'; `$env:JWT_SECRET='$($env:JWT_SECRET)'; `$env:INTERNAL_API_KEY='$($env:INTERNAL_API_KEY)'; & '$py' -m uvicorn api.main:app --host 0.0.0.0 --port 8200"

Start-Sleep -Seconds 3

Write-Host "Starting NLP service (http://localhost:8100)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectDir'; & '$py' nlp_service.py"

Start-Sleep -Seconds 2

Write-Host "Starting ASR backend (ws://localhost:8765)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectDir'; `$env:USE_LOCAL_MIC='False'; `$env:WHISPER_MODEL='$($env:WHISPER_MODEL)'; `$env:CHUNK_DURATION='$($env:CHUNK_DURATION)'; `$env:SUMMARY_INTERVAL='$($env:SUMMARY_INTERVAL)'; `$env:SUMMARY_WINDOW='$($env:SUMMARY_WINDOW)'; `$env:AUTH_API_URL='$($env:AUTH_API_URL)'; `$env:INTERNAL_API_KEY='$($env:INTERNAL_API_KEY)'; `$env:WHISPER_LANGUAGE='$($env:WHISPER_LANGUAGE)'; `$env:LM_CORRECTION_ENABLED='$($env:LM_CORRECTION_ENABLED)'; `$env:RMS_MIN_LEVEL='$($env:RMS_MIN_LEVEL)'; `$env:VAD_MIN_VOICED_RATIO='$($env:VAD_MIN_VOICED_RATIO)'; `$env:MIN_SEGMENT_LOGPROB='$($env:MIN_SEGMENT_LOGPROB)'; `$env:NLP_SERVICE_URL='http://localhost:8100'; `$env:RECORD_DEBUG_AUDIO='False'; & '$py' realtime_transcriber.py"

Start-Sleep -Seconds 2

Write-Host "Starting WebRTC ingest (http://localhost:8081)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectDir'; & '$py' webrtc_ingest.py"

Start-Sleep -Seconds 1

Write-Host "Starting frontend (http://localhost:3000)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectDir\frontend_dashboard'; npm run dev"

Write-Host ""
Write-Host "Meeting UI:  http://localhost:3000"
Write-Host "Login:       http://localhost:3000/login"
Write-Host "Admin panel: http://localhost:3000/admin  (register first user = admin)"
Write-Host "Auth API:    http://localhost:8200/docs"
