# B2B Soft Inventory Audit V2 — Integration Checklist

Complete step-by-step checklist for integrating GFH Audit Automation patterns into V2.

**Status**: Ready to integrate  
**Time Estimate**: 3-4 hours  
**Risk Level**: Low (changes are additive, fallbacks preserved)

---

## Phase 1: Enhanced Web Scraper (2 hours)

### 1.1 Review Enhanced Scraper
- [ ] Read `enhanced_web_scraper_v2.py` (500+ lines)
- [ ] Understand `AuthenticationState` enum
- [ ] Review exception hierarchy (`TwoFactorRequired`, `TurnstileDetected`)
- [ ] Check timeout configurations (20s login, 120s 2FA, 180s verification)

### 1.2 Create B2BSoftScraper Subclass
- [ ] In `web_scraper.py`, add import:
  ```python
  from enhanced_web_scraper_v2 import EnhancedPortalScraper, TwoFactorRequired, TurnstileDetected
  ```
- [ ] Create new class:
  ```python
  class B2BSoftScraper(EnhancedPortalScraper):
      @property
      def portal_url(self) -> str:
          return "https://wsreports.b2bsoft.com/#"
      
      def is_authenticated(self) -> bool:
          try:
              # B2B Soft shows password field when logged out
              return not bool(self.dm.driver.find_elements(
                  By.CSS_SELECTOR, "input[type='password']"))
          except:
              return False
  ```
- [ ] Update old login code to use new class

### 1.3 Add Timeout Configuration
- [ ] Create `audit_config.py` with:
  ```python
  class AuthenticationConfig:
      standard_login_timeout: int = 20
      twofa_timeout: int = 120
      verification_timeout: int = 180
      max_login_retries: int = 3
      retry_delay_base: float = 2
  ```
- [ ] Update `B2BSoftScraper.__init__()` to accept config

### 1.4 Test Standard Login
- [ ] Run app without 2FA
- [ ] Verify: Login completes in 8-12 seconds
- [ ] Check: No crashes when entering credentials
- [ ] Verify: Profile cookies saved (if using profile_dir)

**Checklist Items**: 4/4  
**Estimated Time**: 1 hour

---

## Phase 2: 2FA & Verification Handling (1.5 hours)

### 2.1 Integrate Exception Handling
- [ ] Update `audit_workflow_manager.py`:
  ```python
  try:
      scraper.login()
  except TwoFactorRequired:
      self.status_label.config(text="Waiting for 2FA (2 minutes)...")
      self.root.update()
      scraper._wait_for_2fa_completion(timeout=120)
  except TurnstileDetected:
      self.status_label.config(text="Solving CAPTCHA (3 minutes)...")
      self.root.update()
      scraper._wait_for_turnstile_completion(timeout=180)
  except PortalAuthError as e:
      self.status_label.config(text=f"Error: {e}")
  ```

### 2.2 Update UI Status Messages
- [ ] Tab 1 authentication status should show:
  - [ ] "Logging in..."
  - [ ] "Waiting for 2FA verification (timeout: 2 min)"
  - [ ] "Waiting for CAPTCHA verification (timeout: 3 min)"
  - [ ] "✓ Authenticated"
  - [ ] "✗ Authentication failed: [reason]"

### 2.3 Add Profile Directory Support
- [ ] In `credential_manager.py`:
  ```python
  PROFILE_DIR = Path(os.getenv('LOCALAPPDATA')) / \
      "B2BSoft_Inventory_Audit" / "browser_profile"
  ```
- [ ] Pass `profile_dir=PROFILE_DIR` to scraper
- [ ] Verify cookies persist across app restarts

### 2.4 Test 2FA Flow
- [ ] Enable 2FA on test account
- [ ] Run app and trigger login
- [ ] Wait for 2FA prompt
- [ ] Verify: "Waiting for 2FA" message appears
- [ ] Enter 2FA code
- [ ] Verify: Login completes within 2 minutes
- [ ] Check: App continues automatically

### 2.5 Test Profile Persistence
- [ ] First run: Login normally
- [ ] Close app
- [ ] Second run: Verify logged in without re-entering credentials
- [ ] Check: No "Waiting for 2FA" — cookies worked

**Checklist Items**: 5/5  
**Estimated Time**: 1.5 hours

---

## Phase 3: WhatsApp Window Management (1 hour)

### 3.1 Review Window Manager
- [ ] Read `whatsapp_window_manager_v2.py` (300+ lines)
- [ ] Understand save/restore mechanism
- [ ] Review focus methods (ctypes → pygetwindow → direct)
- [ ] Check timing configurations

### 3.2 Update whatsapp_manager.py
- [ ] Add import:
  ```python
  from whatsapp_window_manager_v2 import WhatsAppWindowManager
  ```
- [ ] Replace `_force_focus_whatsapp()` with:
  ```python
  def _force_focus_whatsapp_with_restore(self):
      """Focus WhatsApp with automatic window restoration"""
      manager = WhatsAppWindowManager(self.root, debug=self.debug)
      return manager.focus_whatsapp(auto_restore=True)
  ```

### 3.3 Integrate Context Manager
- [ ] Find all places that call `_force_focus_whatsapp()`:
  ```bash
  grep -n "_force_focus_whatsapp" whatsapp_manager.py audit_workflow_manager.py B2BSoft_Inventory_Audit_v2.py
  ```
- [ ] Replace with context manager:
  ```python
  from whatsapp_window_manager_v2 import WhatsAppWindowManager
  
  with WhatsAppWindowManager(self) as manager:
      # WhatsApp is focused here
      self._send_message()
      # Window is automatically restored
  ```

### 3.4 Test Window Stability
- [ ] Move app window to custom position (e.g., left half of screen)
- [ ] Send message to WhatsApp
- [ ] Verify: App window stays in same position after send
- [ ] Check: No resize/shift behavior
- [ ] Try with maximized window → verify stays maximized

### 3.5 Test Multiple Sends
- [ ] Send 5+ messages in quick succession
- [ ] Verify: Window position doesn't drift
- [ ] Check: No cumulative shift behavior

**Checklist Items**: 5/5  
**Estimated Time**: 1 hour

---

## Phase 4: Table Scraping Optimization (30 mins)

### 4.1 Enable BeautifulSoup
- [ ] Verify in `requirements.txt`:
  ```
  beautifulsoup4>=4.12
  ```
- [ ] Install: `pip install beautifulsoup4`

### 4.2 Use Scraper Tables Method
- [ ] Replace manual table parsing with:
  ```python
  def get_count_details(scraper) -> List[dict]:
      """Get count details using fast BeautifulSoup parsing"""
      records = scraper.scrape_tables_as_records(min_rows=5)
      if not records:
          raise PortalAuthError("No count details found")
      return records
  ```

### 4.3 Add District Filtering
- [ ] In `data_parser.py`, add:
  ```python
  from difflib import SequenceMatcher
  
  def normalize_district(text: str) -> str:
      return text.lower().strip().replace(' ', '').replace('_', '')
  
  def find_district_records(records: List[dict], district: str) -> List[dict]:
      if not district:
          return records
      
      wanted = normalize_district(district)
      matches = []
      for record in records:
          for key, value in record.items():
              if normalize_district(key) in {"district", "region", "market"}:
                  if wanted in normalize_district(str(value)):
                      matches.append(record)
                      break
      
      return matches or records
  ```

### 4.4 Test Performance
- [ ] Scrape large report (1000+ rows)
- [ ] Time BeautifulSoup parsing: should be <1 second
- [ ] Compare with old Selenium DOM: should be 50x faster
- [ ] Verify data accuracy (no rows lost)

**Checklist Items**: 4/4  
**Estimated Time**: 30 minutes

---

## Phase 5: Testing (1 hour)

### 5.1 Unit Tests
- [ ] Test `detect_auth_state()` detects all states
- [ ] Test `detect_turnstile()` finds iframe
- [ ] Test `detect_two_factor()` finds 2FA fields
- [ ] Test window save/restore doesn't crash
- [ ] Test exception hierarchy (correct exceptions raised)

### 5.2 Integration Tests
- [ ] Full login flow (no 2FA)
- [ ] Full login flow (with 2FA, manual entry)
- [ ] Full login flow (with CAPTCHA, manual solve)
- [ ] Multiple sends without window shift
- [ ] Profile persistence across restart
- [ ] Retry logic (simulate network error)

### 5.3 Stress Tests
- [ ] 10 consecutive sends to WhatsApp
- [ ] Window should not move or resize
- [ ] No cumulative drift in position
- [ ] Memory usage stable (no leaks)

### 5.4 Regression Tests
- [ ] Old login still works (fallback to simple method)
- [ ] OCR IMEI processing still works
- [ ] WhatsApp Desktop integration still works
- [ ] File exports still work
- [ ] Database still persists correctly

**Checklist Items**: 4/4  
**Estimated Time**: 1 hour

---

## Phase 6: Documentation & Deployment (30 mins)

### 6.1 Update README
- [ ] Document new timeout configurations
- [ ] Explain 2FA/CAPTCHA auto-handling
- [ ] Note profile persistence benefit
- [ ] Add troubleshooting section

### 6.2 Create Deployment Notes
- [ ] List all new dependencies:
  - [ ] selenium>=4.15
  - [ ] beautifulsoup4>=4.12
  - [ ] pyautogui
  - [ ] pywin32
  - [ ] pygetwindow (optional but recommended)
- [ ] Create install script:
  ```bash
  pip install -r requirements.txt
  ```

### 6.3 Build & Test EXE
- [ ] Update `B2BSoft_Inventory_Audit_v2.spec`:
  ```python
  hiddenimports=[
      'selenium', 'beautifulsoup4', 'pyautogui', 
      'pywin32', 'ctypes', 'win32gui'
  ]
  ```
- [ ] Build: `pyinstaller B2BSoft_Inventory_Audit_v2.spec`
- [ ] Test EXE on clean Windows VM
- [ ] Verify all features work

### 6.4 Deploy
- [ ] Commit to GitHub:
  ```bash
  git add .
  git commit -m "Integrate GFH patterns: enhanced auth, 2FA handling, window fix"
  git push
  ```
- [ ] Tag release:
  ```bash
  git tag -a v2.1 -m "Enhanced auth, 2FA/CAPTCHA support, window stability"
  git push --tags
  ```

**Checklist Items**: 4/4  
**Estimated Time**: 30 minutes

---

## Summary Table

| Phase | Component | Time | Status |
|-------|-----------|------|--------|
| 1 | Enhanced Web Scraper | 1h | ⏳ Not Started |
| 2 | 2FA & Verification | 1.5h | ⏳ Not Started |
| 3 | WhatsApp Window Mgmt | 1h | ⏳ Not Started |
| 4 | Table Scraping | 30m | ⏳ Not Started |
| 5 | Testing | 1h | ⏳ Not Started |
| 6 | Documentation | 30m | ⏳ Not Started |
| **TOTAL** | | **5.5h** | ⏳ Not Started |

---

## Quick Start

### For experienced developers (skip documentation):

```bash
# 1. Copy new files
cp enhanced_web_scraper_v2.py whatsapp_window_manager_v2.py your_project/

# 2. Update imports in web_scraper.py
# 3. Update imports in whatsapp_manager.py
# 4. Test 2FA flow (manually)
# 5. Test window stability (visually)
# 6. Deploy

# Estimated: 2-3 hours
```

### For careful implementation (follow checklist):

```bash
# Follow all phases in INTEGRATION_CHECKLIST.md
# Estimated: 5.5 hours including tests
```

---

## Rollback Plan

If integration causes issues:

```bash
# Restore old code
git revert <commit-hash>

# Or restore specific files
git checkout HEAD~1 web_scraper.py whatsapp_manager.py
```

Old code paths still exist as fallbacks, so no data loss.

---

## Support

**Questions?** Check:
- `INTEGRATION_GFH_LOGIC_TO_V2.md` — Detailed patterns
- `WHATSAPP_WINDOW_FIX_TIMESHEET_GUIDE.md` — Window management
- `enhanced_web_scraper_v2.py` — Source with docstrings
- `whatsapp_window_manager_v2.py` — Source with docstrings

---

## Sign-Off

- [ ] All phases completed
- [ ] All tests pass
- [ ] No regressions detected
- [ ] Documentation updated
- [ ] Deployed to production

**Date Completed**: _______________  
**Deployed By**: _______________  
**Notes**: 

---

**Developed by Abad Umair Channa | Copyright © 2026**
