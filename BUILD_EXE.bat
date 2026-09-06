@echo off
REM GFH Audit Automation - EXE Build Script (Windows)

setlocal enabledelayedexpansion

echo ==========================================
echo GFH Audit Automation - Build EXE
echo ==========================================
echo.

REM Check if all required modules exist
echo Checking required modules...
set "modules=GFH_Audit_Automation.py b2b_scraper.py gfh_timesheet_scraper.py ocr_engine.py audit_scheduler.py database_manager.py credential_manager.py theme_manager.py header_manager.py two_sheet_processor.py"

for %%M in (%modules%) do (
    if exist "%%M" (
        echo ✓ %%M
    ) else (
        echo ✗ MISSING: %%M
    )
)

echo.
echo Installing dependencies...
pip install pyinstaller --quiet
pip install selenium beautifulsoup4 requests pandas openpyxl pytesseract pillow opencv-python --quiet

echo.
echo Building EXE...
pyinstaller --onefile ^
    --windowed ^
    --icon=gfh_icon.ico ^
    --add-data="gfh_icon.ico;." ^
    --hidden-import=selenium ^
    --hidden-import=bs4 ^
    --hidden-import=requests ^
    --hidden-import=pandas ^
    --hidden-import=openpyxl ^
    --hidden-import=pytesseract ^
    --hidden-import=PIL ^
    --hidden-import=cv2 ^
    --hidden-import=cryptography.fernet ^
    GFH_Audit_Automation.py

echo.
if exist "dist\GFH_Audit_Automation.exe" (
    echo ✅ BUILD SUCCESSFUL!
    echo 📁 Location: dist\GFH_Audit_Automation.exe
    dir dist\GFH_Audit_Automation.exe
) else (
    echo ❌ Build failed
    exit /b 1
)

echo.
echo Ready for deployment!
pause
