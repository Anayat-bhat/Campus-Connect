@echo off
REM CampusConnect: One-Click Modern Web & Mobile App Launcher
TITLE CampusConnect - Web & Mobile PWA Server

echo ======================================================================
echo    Starting CampusConnect Modern Web & Mobile App...
echo ======================================================================

REM Check Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in PATH.
    pause
    exit /b 1
)

REM Activate virtual environment if present
IF EXIST "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo [INFO] Starting Web & Mobile Application on http://localhost:5000 ...
echo [INFO] Opening default browser...
start "" "http://localhost:5000"

python web_app.py --port 5000

exit /b 0
