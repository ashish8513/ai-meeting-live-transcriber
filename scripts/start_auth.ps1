# Start Auth API only (port 8200)
$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectDir

$py = Join-Path $ProjectDir "venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

if (Test-Path "$ProjectDir\.env") { . "$ProjectDir\scripts\load_dotenv.ps1" }
if (-not $env:DATABASE_URL) { $env:DATABASE_URL = "sqlite:///./data/meetscribe.db" }

$on8200 = Get-NetTCPConnection -LocalPort 8200 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($on8200) {
    Stop-Process -Id $on8200.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Host "Stopped old process on port 8200 (PID $($on8200.OwningProcess))"
}

Write-Host "Auth API: http://localhost:8200"
Write-Host "Docs:     http://localhost:8200/docs"
& $py -m uvicorn api.main:app --host 0.0.0.0 --port 8200
