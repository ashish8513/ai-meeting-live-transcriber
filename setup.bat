@echo off
REM Meeting Live Transcribe Model - Setup Script for Windows

echo.
echo =========================================
echo Meeting Live Transcribe - Setup
echo =========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://www.python.org
    pause
    exit /b 1
)

echo [1/5] Python version check - OK
python --version

REM Create virtual environment
if not exist venv (
    echo [2/5] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created - OK
) else (
    echo [2/5] Virtual environment already exists - OK
)

REM Activate virtual environment
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo [4/5] Installing requirements...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)
echo Requirements installed - OK

echo [5/5] Setup complete!
echo.
echo =========================================
echo Next steps:
echo =========================================
echo.
echo 1. To start the backend transcriber:
echo    run_backend.bat
echo.
echo 2. To start only the main ASR service:
echo    python realtime_transcriber.py
echo.
echo 3. To check available microphones:
echo    python mic_check.py
echo.
echo 4. To test WebSocket connection:
echo    python client_test.py
echo.
echo 5. To start the frontend dashboard:
echo    cd frontend_dashboard
echo    npm install
echo    npm run dev
echo.
pause
