@echo off
REM CampusConnect: Windows One-Click Application Launcher
TITLE CampusConnect - Smart Campus Lost ^& Found System

echo ======================================================================
echo    Starting CampusConnect Desktop System...
echo ======================================================================

REM Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in PATH. Please install Python 3.10 or higher.
    pause
    exit /b 1
)

REM Activate virtual environment if present
IF EXIST "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Run application
echo [INFO] Launching CampusConnect GUI...
python main.py

exit /b 0
