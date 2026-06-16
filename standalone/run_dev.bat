@echo off
REM Run without building an .exe -- useful for development/testing
echo Starting Supplier Scraper (dev mode)...

REM ── Check for Python ───────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Python is not installed or not on PATH.
    echo  Trying to install it automatically via winget...
    echo.
    winget install Python.Python.3 --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
    if errorlevel 1 (
        echo  Auto-install failed. Please install Python manually:
        echo.
        echo    1. Go to: https://www.python.org/downloads/
        echo    2. Download and run the installer
        echo    3. IMPORTANT: check "Add python.exe to PATH" before clicking Install
        echo    4. Re-run this script after installing
        echo.
        start https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo  Python installed. Restarting script...
    echo.
    REM Refresh PATH so python is available in this session
    call refreshenv >nul 2>&1
    python --version >nul 2>&1
    if errorlevel 1 (
        echo  Python was installed but PATH was not updated yet.
        echo  Please close this window and re-run run_dev.bat.
        pause
        exit /b 1
    )
)

REM ── Install dependencies ───────────────────────────────────────────────────
echo Installing dependencies...
python -m pip install -r requirements_standalone.txt -q

REM ── First-time config ──────────────────────────────────────────────────────
if not exist config.ini (
    copy config.ini.example config.ini >nul
    echo.
    echo  Created config.ini -- fill in your API keys, then re-run this script.
    notepad config.ini
    pause
    exit /b 0
)

REM ── Launch ─────────────────────────────────────────────────────────────────
python cli.py serve
pause
