# Meeting Live Transcribe Model - Simple Backend Starter
# Usage: .\start_backend_simple.ps1

param(
    [switch]$SkipSetup = $false
)

# Get current directory
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommandPath
Set-Location $ProjectDir

Write-Host "================================"
Write-Host "Meeting Live Transcribe Backend"
Write-Host "================================" -ForegroundColor Green
Write-Host ""

# Check Python
$PythonCmd = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    Write-Host "Please install Python 3.11+ from https://www.python.org" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Python found: $PythonCmd" -ForegroundColor Green

# Check/create venv
if (-not (Test-Path "venv")) {
    Write-Host "[!] Virtual environment not found. Creating..."
    python -m venv venv
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "[OK] Virtual environment exists" -ForegroundColor Green
}

# Activate venv
Write-Host "[*] Activating virtual environment..."
& ".\venv\Scripts\Activate.ps1"

# Check if we need to install requirements
if ($SkipSetup) {
    Write-Host "[*] Skipping dependency installation..." -ForegroundColor Yellow
} else {
    Write-Host "[*] Installing requirements..."
    pip install -r requirements.txt --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install requirements" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Requirements installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================"
Write-Host "Starting Backend Services"
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Environment Variables:" -ForegroundColor Yellow
Write-Host "  WHISPER_MODEL: $($env:WHISPER_MODEL -or 'small.en')"
Write-Host "  DEVICE_ID: $($env:DEVICE_ID -or '1')"
Write-Host "  USE_LOCAL_MIC: $($env:USE_LOCAL_MIC -or 'False')"
Write-Host ""
Write-Host "Services starting..." -ForegroundColor Cyan
Write-Host ""

# Set some reasonable defaults if not set
if (-not $env:WHISPER_MODEL) { $env:WHISPER_MODEL = "small.en" }
if (-not $env:WHISPER_LANGUAGE) { $env:WHISPER_LANGUAGE = "auto" }
if (-not $env:SUMMARY_INTERVAL) { $env:SUMMARY_INTERVAL = "300" }
if (-not $env:SUMMARY_WINDOW) { $env:SUMMARY_WINDOW = "300" }
if (-not $env:LM_CORRECTION_ENABLED) { $env:LM_CORRECTION_ENABLED = "True" }
if (-not $env:USE_LOCAL_MIC) { $env:USE_LOCAL_MIC = "False" }
if (-not $env:CHUNK_DURATION) { $env:CHUNK_DURATION = "1.2" }
if (-not $env:RECORD_DEBUG_AUDIO) { $env:RECORD_DEBUG_AUDIO = "False" }
if (-not $env:DEVICE_ID) { $env:DEVICE_ID = "1" }
if (-not $env:USE_LOCAL_MIC) { $env:USE_LOCAL_MIC = "False" }
if (-not $env:RECORD_DEBUG_AUDIO) { $env:RECORD_DEBUG_AUDIO = "False" }

# Start the main transcriber
Write-Host "[*] Starting ASR Backend (realtime_transcriber.py)..." -ForegroundColor Cyan
Write-Host "    WebSocket: ws://0.0.0.0:8765" -ForegroundColor Gray
Write-Host ""

python realtime_transcriber.py

# If we get here, the backend has stopped
Write-Host ""
Write-Host "Backend stopped." -ForegroundColor Yellow
pause
