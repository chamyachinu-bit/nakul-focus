@echo off
echo ============================================================
echo   NAKUL FOCUS SYSTEM — SETUP
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)

echo [1/3] Installing Python dependencies...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)

echo [2/3] Initializing database...
python database.py

echo [3/3] Running setup...
python main.py setup

echo.
echo ============================================================
echo   SETUP COMPLETE!
echo.
echo   START COMMANDS:
echo     python main.py               -- show daily status
echo     python main.py dashboard     -- open browser dashboard
echo     python main.py timer         -- start focus timer
echo     python main.py habits        -- view habit checklist
echo     python main.py reminders start -- start reminder service
echo.
echo   NOTE: For website blocking, run as Administrator:
echo     Right-click this bat file -> Run as administrator
echo ============================================================
echo.
pause
