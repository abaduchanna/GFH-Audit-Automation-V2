# GFH AUDIT AUTOMATION - DEPLOYMENT GUIDE

**Version:** 1.0  
**Build Date:** 2026-09-05  
**Status:** ✅ PRODUCTION READY

---

## 🚀 QUICK START

### Option A: Run EXE (Easiest)
1. Download `GFH_Audit_Automation.exe` from releases
2. Double-click to run
3. No installation required

### Option B: Run from Source
1. Install Python 3.9+
2. `pip install -r requirements.txt`
3. Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
4. `python GFH_Audit_Automation.py`

---

## 📦 SYSTEM REQUIREMENTS

**Windows:**
- Windows 10/11 (x86_64)
- 500MB free disk space
- Chrome or Chromium installed

**Python (if running from source):**
- Python 3.9+
- pip package manager

**System Binary (for OCR):**
- Tesseract-OCR (https://github.com/UB-Mannheim/tesseract/wiki)

---

## 🔧 INSTALLATION

### Windows (EXE)
1. Download `GFH_Audit_Automation.exe`
2. Place in desired folder
3. Double-click to run
4. (Optional) Create shortcut for desktop access

### Windows (Source Code)
```batch
# Install dependencies
pip install -r requirements.txt

# Install Tesseract
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Or via chocolatey: choco install tesseract
```

---

## 🏗️ BUILD EXE FROM SOURCE

### Windows
```batch
# 1. Navigate to project directory
cd C:\path\to\GFH-Audit-Automation-V2

# 2. Run build script
BUILD_EXE.bat

# 3. EXE will be created in dist\ folder
# dist\GFH_Audit_Automation.exe
```

### Linux/Mac
```bash
# 1. Navigate to project directory
cd /path/to/GFH-Audit-Automation-V2

# 2. Run build script
chmod +x BUILD_EXE.sh
./BUILD_EXE.sh

# 3. EXE will be created in dist/ folder
```

---

## ⚙️ CONFIGURATION

### First Run Setup

1. **B2B Portal Credentials**
   - Access Code: `9909129` (pre-filled)
   - Account ID: Enter your account ID
   - Username: Enter B2B username
   - Password: Enter B2B password
   - Click "Save"

2. **GFH Timesheet Credentials**
   - Email: Enter timesheet email
   - Password: Enter timesheet password
   - Click "Save"

3. **Scheduler Configuration**
   - Set trigger time (e.g., `09:00`)
   - Click "Enable Scheduler"
   - Status should show "ENABLED - 09:00"

### Testing

1. Click "Test" button for B2B login
2. Click "Test" button for Timesheet login
3. Click "Auto-Fetch" to download files manually
4. Verify file paths show in Auto-Import Status

---

## 🎯 HOW TO USE

### Manual Audit

1. Enter B2B and Timesheet credentials
2. Click "Auto-Fetch" for B2B
3. Click "Auto-Fetch" for Timesheet
4. Files will export to temp folder
5. Inventory status shows automatically
6. Variances will be calculated
7. WhatsApp messages send automatically

### Scheduled Audit

1. Configure credentials (as above)
2. Set scheduler time (e.g., 09:00 AM)
3. Click "Enable Scheduler"
4. App will monitor time in background
5. At scheduled time, audit runs automatically
6. 3 escalation reminders at 45-min intervals
7. OCR listener monitors WhatsApp for images
8. IMEIs auto-deducted from variance list

---

## 📊 FEATURES

✅ **Automatic Data Extraction**
- B2B Soft inventory export (Selenium automation)
- GFH timesheet fetch (BeautifulSoup + HTTP)

✅ **Time-Based Scheduling**
- Set trigger time (HH:MM format)
- Background monitoring thread
- Enable/disable controls

✅ **Escalation Reminders**
- 3 automatic reminders (45-min intervals)
- Sent via WhatsApp
- Configurable per district

✅ **OCR Image Processing**
- Tesseract-based IMEI extraction
- WhatsApp image monitoring
- Auto-deduct cleared items
- Luhn algorithm validation

✅ **WhatsApp Integration**
- Kickoff notifications
- Escalation reminders
- Final reports
- Per-district messaging

✅ **Variance Processing**
- B2B vs Timesheet comparison
- Two-sheet logic matching
- Store/employee reconciliation
- Real-time UI updates

✅ **Professional UI**
- Dark/light theme toggle
- GFH branding
- Real-time status display
- Event log

---

## 🔐 SECURITY

**Credentials Encryption:**
- All passwords encrypted with Fernet (AES-128)
- Stored locally in encrypted database
- Never sent over unencrypted connections

**Data Protection:**
- SQLite database with WAL mode
- Regular backups recommended
- Sensitive info masked in UI

---

## 📋 MODULES INCLUDED

| File | Purpose | Lines |
|------|---------|-------|
| GFH_Audit_Automation.py | Main application | 6,500 |
| b2b_scraper.py | B2B portal automation | 246 |
| gfh_timesheet_scraper.py | Timesheet fetcher | 252 |
| ocr_engine.py | OCR + reconciliation | 278 |
| audit_scheduler.py | Background scheduler | 188 |
| database_manager.py | SQLite manager | - |
| credential_manager.py | Encryption manager | - |
| theme_manager.py | UI theming | - |
| header_manager.py | Header display | - |
| two_sheet_processor.py | Data merging | - |

---

## 🐛 TROUBLESHOOTING

### Issue: "Chrome driver not found"
**Solution:** Install Chrome or Chromium
- Windows: Download from google.com/chrome
- Linux: `sudo apt-get install chromium-browser`

### Issue: "Tesseract not found"
**Solution:** Install Tesseract-OCR
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Linux: `sudo apt-get install tesseract-ocr`

### Issue: "B2B login fails"
**Solution:** Verify credentials
- Check "Test Login" button
- Confirm Access Code = `9909129`
- Verify Account ID is correct

### Issue: "Timesheet fetch returns empty"
**Solution:** Check app URL configuration
- May need to update `BASE_URL` in `gfh_timesheet_scraper.py`
- Confirm email/password are correct

### Issue: "OCR not extracting IMEIs"
**Solution:** Verify image quality
- Ensure WhatsApp images are clear
- Check Tesseract is installed
- Try manual test with sample image

---

## 📞 SUPPORT

**Developer:** Abad Umair Channa  
**Email:** abaduchanna@gmail.com  
**GitHub:** https://github.com/abaduchanna/vidapay-gfh

**Issues/Feedback:**
- Create GitHub issue with error message
- Include screenshots if possible
- Provide steps to reproduce

---

## 📝 CHANGELOG

### v1.0 (2026-09-05)
- ✅ Initial release
- ✅ All 5 integration phases complete
- ✅ B2B scraper (Selenium)
- ✅ Timesheet scraper (BeautifulSoup)
- ✅ OCR engine (Tesseract)
- ✅ Scheduler with reminders
- ✅ Full WhatsApp integration
- ✅ Professional UI

---

## 📄 LICENSE

Copyright © 2026 Abad Umair Channa. All rights reserved.

---

## 🎉 READY TO USE

All code tested and verified.  
No additional development needed.  
Ready for production deployment.

Download EXE and run!
