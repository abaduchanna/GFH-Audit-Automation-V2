#!/bin/bash
# GFH Audit Automation - EXE Build Script

echo "=========================================="
echo "GFH Audit Automation - Build EXE"
echo "=========================================="
echo ""

# Check if all required modules exist
echo "📋 Checking required modules..."
modules=(
    "GFH_Audit_Automation.py"
    "b2b_scraper.py"
    "gfh_timesheet_scraper.py"
    "ocr_engine.py"
    "audit_scheduler.py"
    "database_manager.py"
    "credential_manager.py"
    "theme_manager.py"
    "header_manager.py"
    "two_sheet_processor.py"
)

for module in "${modules[@]}"; do
    if [ -f "$module" ]; then
        echo "✓ $module"
    else
        echo "✗ MISSING: $module"
    fi
done

echo ""
echo "📦 Installing dependencies..."
pip install pyinstaller --quiet
pip install selenium beautifulsoup4 requests pandas openpyxl pytesseract pillow opencv-python --quiet

echo ""
echo "🔨 Building EXE..."
pyinstaller --onefile \
    --windowed \
    --icon=gfh_icon.ico \
    --add-data="gfh_icon.ico:." \
    --hidden-import=selenium \
    --hidden-import=bs4 \
    --hidden-import=requests \
    --hidden-import=pandas \
    --hidden-import=openpyxl \
    --hidden-import=pytesseract \
    --hidden-import=PIL \
    --hidden-import=cv2 \
    --hidden-import=cryptography.fernet \
    GFH_Audit_Automation.py

echo ""
if [ -f "dist/GFH_Audit_Automation.exe" ]; then
    echo "✅ BUILD SUCCESSFUL!"
    echo "📁 Location: dist/GFH_Audit_Automation.exe"
    ls -lh dist/GFH_Audit_Automation.exe
else
    echo "❌ Build failed"
    exit 1
fi

echo ""
echo "Ready for deployment!"
