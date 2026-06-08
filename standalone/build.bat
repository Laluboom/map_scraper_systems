@echo off
echo ============================================
echo  Supplier Scraper -- Build .exe
echo ============================================

REM Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ from python.org
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements_standalone.txt

REM Build the .exe
echo Building .exe with PyInstaller...
pyinstaller supplier_scraper.spec --clean --noconfirm

echo.
echo ============================================
echo  Build complete!
echo  Your .exe is at: dist\supplier_scraper.exe
echo.
echo  NEXT STEPS:
echo  1. Copy dist\supplier_scraper.exe to your desired folder
echo  2. Run: supplier_scraper.exe setup
echo  3. Edit config.ini with your API keys
echo  4. Run: supplier_scraper.exe serve
echo ============================================
pause
