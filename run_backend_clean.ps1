# Meeting Live Transcribe Model - Complete Backend Launcher
# This script starts all backend services in separate PowerShell windows
# Usage: .\run_backend_clean.ps1

param(
    [switch]$NLPOnly = $false,
    [switch]$ASROnly = $false,
    [switch]$WebRTCOnly = $false,
    [switch]$SkipSetup = $false
)

# Get project directory
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommandPath
Set-Location $ProjectDir

Write-Host ""
Write-Host "╔════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Meeting Live Transcribe - Backend Launcher   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Verify Python
$PythonVersion = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Python not found!" -ForegroundColor Red
    Write-Host "   Please install Python 3.11+ from https://www.python.org" -ForegroundColor Yellow
    pause
    exit 1
}
Write-Host "✅ Python found: $PythonVersion" -ForegroundColor Green

# Setup venv if needed
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
        pause
        exit 1
    }
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✅ Virtual environment exists" -ForegroundColor Green
}

# Install requirements if not skipped
if (-not $SkipSetup) {
    Write-Host "📥 Installing dependencies..."
    $venvPython = ".\venv\Scripts\python.exe"
    & $venvPython -m pip install -r requirements.txt --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Warning: Some dependencies may not have installed" -ForegroundColor Yellow
    } else {
        Write-Host "✅ Dependencies installed" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "📋 Configuration:" -ForegroundColor Cyan
Write-Host "   WHISPER_MODEL: $($env:WHISPER_MODEL -or 'small.en')" -ForegroundColor Gray
Write-Host "   DEVICE_ID: $($env:DEVICE_ID -or '1')" -ForegroundColor Gray
Write-Host "   USE_LOCAL_MIC: $($env:USE_LOCAL_MIC -or 'False')" -ForegroundColor Gray
Write-Host ""

# Set defaults
$env:WHISPER_MODEL = $env:WHISPER_MODEL -or "small.en"
$env:DEVICE_ID = $env:DEVICE_ID -or "1"
$env:USE_LOCAL_MIC = $env:USE_LOCAL_MIC -or "False"
$env:RECORD_DEBUG_AUDIO = $env:RECORD_DEBUG_AUDIO -or "False"
$env:WEBSOCKET_HOST = $env:WEBSOCKET_HOST -or "0.0.0.0"
$env:WEBSOCKET_PORT = $env:WEBSOCKET_PORT -or "8765"

Write-Host "🚀 Starting services..." -ForegroundColor Cyan
Write-Host ""

# Helper function to start service in new window
function Start-Service {
    param(
        [string]$Name,
        [string]$Script,
        [string]$Description,
        [string]$Port
    )
    
    $ActivateCmd = ". '.\venv\Scripts\Activate.ps1'"
    $FullCmd = "$ActivateCmd; python $Script"
    
    Write-Host "   ⏳ Starting $Name ($Description on port $Port)..." -ForegroundColor Yellow
    
    Start-Process powershell -ArgumentList "-NoExit -Command cd '$ProjectDir'; $FullCmd" `
        -WindowStyle Normal
    
    Start-Sleep -Milliseconds 500
}

# Start services based on parameters
if ($NLPOnly) {
    Start-Service "NLP Service" "nlp_service.py" "Text Processing" "8100"
}
elseif ($ASROnly) {
    Start-Service "ASR Backend" "realtime_transcriber.py" "Speech Recognition" "8765"
}
elseif ($WebRTCOnly) {
    Start-Service "WebRTC Ingest" "webrtc_ingest.py" "Browser Audio" "8081"
}
else {
    # Start all services (default)
    Write-Host "   Starting ALL services:" -ForegroundColor Cyan
    Start-Service "NLP Service" "nlp_service.py" "Text Processing" "8100"
    Start-Sleep -Seconds 1
    
    Start-Service "ASR Backend" "realtime_transcriber.py" "Speech Recognition" "8765"
    Start-Sleep -Seconds 1
    
    Start-Service "WebRTC Ingest" "webrtc_ingest.py" "Browser Audio" "8081"
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║           Services Started Successfully        ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📡 Endpoints:" -ForegroundColor Cyan
Write-Host "   WebSocket:    ws://localhost:8765" -ForegroundColor Gray
Write-Host "   NLP Service:  http://localhost:8100" -ForegroundColor Gray
Write-Host "   WebRTC:       http://localhost:8081" -ForegroundColor Gray
Write-Host ""
Write-Host "🌐 Frontend (optional):" -ForegroundColor Cyan
Write-Host "   cd frontend_dashboard && npm run dev" -ForegroundColor Gray
Write-Host "   Then open: http://localhost:3000" -ForegroundColor Gray
Write-Host ""
Write-Host "📝 To test: python client_test.py" -ForegroundColor Gray
Write-Host ""
Write-Host "⏹️  Close the service windows to stop them." -ForegroundColor Yellow
