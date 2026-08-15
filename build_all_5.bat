@echo off
REM ==========================================================================
REM  Build All Fixed Modules — Force Clean EXE Build
REM  Developed by Abad Umair Channa
REM
REM  Builds these 4 modules:
REM    1. gfh-rebate-tools                      -> rebate_tools.exe
REM    2. gfh-xls-to-xlsx                       -> gfh_xls_to_xlsx.exe
REM    3. gfh-accessories-order-history-scraper -> Accessories_order_history_scraper.exe
REM    4. vidapay-gfh (Inventory Audit)         -> GFH_Inventory_Audit.exe
REM
REM  (vidapay-extractor, UPS tracker, and transfer bot are SKIPPED — finalized)
REM
REM  This script does a FRESH git clone of each repo into a _src folder,
REM  so it always builds the latest code from GitHub — even if your local
REM  copies are old, modified, or not git-connected.
REM
REM  USAGE:
REM    1. Double-click build_all_5.bat
REM    2. All .exe files are collected into the output folder
REM
REM  PREREQUISITES:
REM    - Python 3.11+ installed and in PATH
REM    - Git installed and in PATH
REM    - Run once: pip install pyinstaller
REM ==========================================================================

setlocal enabledelayedexpansion
title Build All Fixed Modules

REM ── HARDCODED PATHS ──
set "SRCDIR=C:\Users\AbadUmairChanna\Downloads\github\_src"
set "OUTDIR=C:\Users\AbadUmairChanna\Downloads\github"

echo.
echo  ============================================================
echo   Build All Fixed Modules ^(fresh clone from GitHub^)
echo  ============================================================
echo.
echo   Clone to: %SRCDIR%
echo   Output:   %OUTDIR%
echo.

REM ── Step 0: Verify Python + PyInstaller + Git ──
echo  Step 0: Checking prerequisites...
python --version >nul 2>&1
if errorlevel 1 (
    echo    ERROR: Python not found in PATH. Install Python 3.11+ first.
    echo.
    pause
    exit /b 1
)
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo    PyInstaller not found. Installing...
    python -m pip install --upgrade pyinstaller
)
git --version >nul 2>&1
if errorlevel 1 (
    echo    ERROR: Git not found in PATH. Install Git for Windows.
    echo.
    pause
    exit /b 1
)
echo    Python + PyInstaller + Git OK
echo.

REM ── Step 0b: Redirect PyInstaller workpath to system TEMP ──
REM   Reason: if build/ sits under Downloads\ it can be OneDrive-synced
REM   or scanned aggressively by Windows Defender, which sometimes
REM   quarantines/deletes the build folder mid-build and produces
REM   "FileNotFoundError: base_library.zip". Putting workpath in %TEMP%
REM   avoids both problems.
set "WORKBASE=%TEMP%\pyi_build"
if not exist "%WORKBASE%" mkdir "%WORKBASE%"
echo    Workpath: %WORKBASE%
echo.

REM ── Step 1: Wipe and recreate the _src clone folder ──
echo  Step 1: Preparing fresh clone folder...
if exist "%SRCDIR%" rmdir /s /q "%SRCDIR%"
mkdir "%SRCDIR%"
echo    Ready: %SRCDIR%
echo.

REM ── Define the 4 modules (dir ^ github URL ^ spec) ──
set "M1_DIR=gfh-rebate-tools"
set "M1_URL=https://github.com/abaduchanna/gfh-rebate-tools.git"
set "M1_SPEC=rebate_tools.spec"

set "M2_DIR=gfh-xls-to-xlsx"
set "M2_URL=https://github.com/abaduchanna/gfh-xls-to-xlsx.git"
set "M2_SPEC=gfh_xls_to_xlsx.spec"

set "M3_DIR=gfh-accessories-order-history-scraper"
set "M3_URL=https://github.com/abaduchanna/gfh-accessories-order-history-scraper.git"
set "M3_SPEC=Accessories_order_history_scraper.spec"

set "M4_DIR=vidapay-gfh"
set "M4_URL=https://github.com/abaduchanna/vidapay-gfh.git"
set "M4_SPEC=GFH_Inventory_Audit.spec"

REM ── Step 2: Delete old .exe files from output folder ──
echo  Step 2: Cleaning old .exe files from output...
if not exist "%OUTDIR%" mkdir "%OUTDIR%"
if exist "%OUTDIR%\*.exe" (
    del /f /q "%OUTDIR%\*.exe" 2>nul
    echo    Deleted old .exe files
) else (
    echo    No old .exe files to delete
)
echo.

set BUILD_COUNT=0
set FAIL_COUNT=0

REM ── Step 3: Clone + build each module ──
echo  Step 3: Cloning from GitHub and building...
echo.

for /L %%N in (1,1,4) do (
    call :CLONE_AND_BUILD %%N
)

echo.
echo  ============================================================
echo   Build Summary
echo  ============================================================
echo    Successful builds: !BUILD_COUNT!
echo    Failed builds:     !FAIL_COUNT!
echo.

REM ── Step 4: Clear Windows icon cache so new .exe icons show ──
echo  Step 4: Clearing Windows icon cache...
del /f /q "%localappdata%\IconCache.db" 2>nul
del /f /q "%localappdata%\Microsoft\Windows\Explorer\iconcache_*.db" 2>nul
ie4uinit.exe -show 2>nul
echo    Icon cache cleared.
echo.

REM ── List collected .exe files ──
echo  ============================================================
echo  Collected .exe files in %OUTDIR%:
echo  ============================================================
if exist "%OUTDIR%\*.exe" (
    dir "%OUTDIR%\*.exe" | findstr ".exe"
    echo.
    echo  Full paths:
    for %%E in ("%OUTDIR%\*.exe") do (
        echo    %%~fE
    )
) else (
    echo  WARNING: no .exe files found — all builds may have failed
)

echo.
echo  ============================================================
echo   Done!
echo  ============================================================
echo.
pause
endlocal
exit /b 0


REM ==========================================================================
REM  Subroutine: CLONE_AND_BUILD
REM    %1 = module index (1..4)
REM ==========================================================================
:CLONE_AND_BUILD
set "IDX=%1"

set "MDIR=!M%IDX%_DIR!"
set "MURL=!M%IDX%_URL!"
set "MSPEC=!M%IDX%_SPEC!"

echo  ============================================================
echo  [!IDX!/4] !MDIR!
echo  ============================================================
echo    Cloning from !MURL! ...

REM Clone fresh from GitHub into _src\<module>
git clone "!MURL!" "%SRCDIR%\!MDIR!" 2>&1
if errorlevel 1 (
    echo    FAILED to clone: !MDIR!
    set /a FAIL_COUNT+=1
    echo.
    goto :EOF
)

echo    Clone OK.
echo.

REM Enter the module folder
pushd "%SRCDIR%\!MDIR!"

REM Clean previous build artifacts (local + temp workpath)
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"
del /s /q *.pyc 2>nul
if exist "%WORKBASE%\!MDIR!" rmdir /s /q "%WORKBASE%\!MDIR!"
mkdir "%WORKBASE%\!MDIR!" 2>nul

REM Install deps if requirements.txt exists
if exist "requirements.txt" (
    echo    Installing requirements...
    python -m pip install -r requirements.txt --quiet 2>nul
)

REM Derive the .exe name from the spec name (spec.spec -> spec.exe)
set "EXENAME=!MSPEC:.spec=.exe!"

echo  ------------------------------------------------------------
echo  Building: !MDIR!\!MSPEC!
echo  ------------------------------------------------------------

REM Build (workpath in system TEMP to avoid OneDrive + Defender issues)
python -m PyInstaller "!MSPEC!" --noconfirm --clean --workpath "%WORKBASE%\!MDIR!" 2>&1

if errorlevel 1 (
    echo    FAILED: !MDIR!\!MSPEC!
    set /a FAIL_COUNT+=1
) else (
    echo    SUCCESS: !MDIR!\!MSPEC!
    set /a BUILD_COUNT+=1
    REM Copy the .exe to the output folder
    if exist "dist\!EXENAME!" (
        copy /Y "dist\!EXENAME!" "%OUTDIR%\!EXENAME!" >nul
        echo    Collected: %OUTDIR%\!EXENAME!
    ) else (
        echo    WARNING: dist\!EXENAME! not found after build
    )
)

popd
echo.
goto :EOF
