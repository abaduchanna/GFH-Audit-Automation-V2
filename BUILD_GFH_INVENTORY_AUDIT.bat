@echo off
REM ============================================================================
REM GFH Inventory Audit — PyInstaller Build Script
REM Developed by Abad Umair Channa | Copyright © 2026 | All rights reserved.
REM ============================================================================
REM
REM This script builds the GFH Inventory Audit EXE with:
REM   • Taskbar icon support (gfh_icon.ico)
REM   • Embedded resources (logos, stores config, theme manager)
REM   • All dependencies bundled (Selenium, openpyxl, PIL, pyautogui, etc.)
REM   • No console window (windowed mode)
REM   • DPI-aware rendering
REM
REM Usage:
REM   1. Place this file in the repo root directory
REM   2. Open Command Prompt in the repo root
REM   3. Run: BUILD_GFH_INVENTORY_AUDIT.bat
REM   4. Output EXE will be in: dist\GFH_Inventory_Audit.exe
REM
REM Prerequisites:
REM   • Python 3.10+ installed and in PATH
REM   • PyInstaller installed: pip install pyinstaller
REM   • All dependencies installed: pip install -r requirements.txt
REM
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo GFH Inventory Audit — Building EXE with Taskbar Icon Support
echo ============================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo ✓ Python found
python --version

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo.
    echo Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo ✓ PyInstaller found

REM Check if GFH_Inventory_Audit.spec exists
if not exist "GFH_Inventory_Audit.spec" (
    echo.
    echo ERROR: GFH_Inventory_Audit.spec not found in current directory
    echo Make sure you're running this from the repository root
    pause
    exit /b 1
)

echo ✓ Spec file found (GFH_Inventory_Audit.spec)

REM Check if icon exists
if not exist "gfh_icon.ico" (
    echo.
    echo WARNING: gfh_icon.ico not found
    echo The EXE will still build but won't have a taskbar icon
    echo.
) else (
    echo ✓ Icon file found (gfh_icon.ico)
)

REM Clean previous build artifacts
echo.
echo Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build" >nul 2>&1
if exist "dist" rmdir /s /q "dist" >nul 2>&1
if exist "__pycache__" rmdir /s /q "__pycache__" >nul 2>&1

echo ✓ Cleaned build directories

REM Build with PyInstaller
echo.
echo Building GFH_Inventory_Audit.exe...
echo This may take 2-5 minutes on first run...
echo ============================================================================

REM ── Redirect workpath to TEMP to avoid OneDrive sync issues ──
set "WORKBASE=%TEMP%\pyi_build\GFH_Inventory_Audit"
if exist "%WORKBASE%" rmdir /s /q "%WORKBASE%"
mkdir "%WORKBASE%" 2>nul

pyinstaller GFH_Inventory_Audit.spec --clean --noconfirm --workpath "%WORKBASE%"

if errorlevel 1 (
    echo.
    echo ============================================================================
    echo ERROR: Build failed!
    echo ============================================================================
    echo.
    echo Possible solutions:
    echo 1. Make sure all dependencies are installed:
    echo    pip install -r requirements.txt
    echo 2. Check that all referenced files exist (logos, config files)
    echo 3. Check PyInstaller version: pip install --upgrade pyinstaller
    echo 4. Try deleting build/ and dist/ folders and rebuilding
    echo.
    pause
    exit /b 1
)

REM Verify the output
if not exist "dist\GFH_Inventory_Audit.exe" (
    echo.
    echo ============================================================================
    echo ERROR: EXE not found in dist directory
    echo ============================================================================
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo ✅ BUILD SUCCESSFUL
echo ============================================================================
echo.

REM Get file size
for %%A in ("dist\GFH_Inventory_Audit.exe") do (
    set /A size=%%~zA
    set /A sizeMB=!size!/1048576
    echo Output EXE: dist\GFH_Inventory_Audit.exe
    echo Size: !size! bytes (!sizeMB! MB^)
)

echo.
echo Features Included:
echo   ✓ Taskbar icon (gfh_icon.ico)
echo   ✓ No console window (windowed mode)
echo   ✓ All dependencies bundled
echo   ✓ Embedded resources (logos, config, theme)
echo   ✓ Single-file deployment ready
echo   ✓ DPI-aware rendering
echo.
echo Next Steps:
echo 1. Test the EXE: dist\GFH_Inventory_Audit.exe
echo 2. Verify taskbar icon appears in Windows taskbar
echo 3. Copy to production folder when ready
echo.

REM Open the dist folder
echo Opening dist folder...
start "" "dist\"

echo.
echo Done! Press any key to exit...
pause >nul
exit /b 0
