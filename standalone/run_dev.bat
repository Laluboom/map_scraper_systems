@echo off
REM Run without building an .exe -- useful for development/testing
echo Starting Supplier Scraper (dev mode)...

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    pause
    exit /b 1
)

pip install -r requirements_standalone.txt -q

REM Copy config if it doesn't exist
if not exist config.ini (
    copy config.ini.example config.ini
    echo Created config.ini -- please fill in your API keys, then re-run this script.
    notepad config.ini
    pause
    exit /b 0
)

python cli.py serve
pause
