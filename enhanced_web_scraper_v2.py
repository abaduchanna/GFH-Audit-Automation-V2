"""
Enhanced Web Scraper Module for B2B Soft Inventory Audit v2
Incorporates robust authentication, 2FA handling, and error recovery from GFH Audit Automation

Features:
- Extended timeouts for 2FA challenges
- Profile persistence (cookies survive across runs)
- Retry logic with exponential backoff
- Human verification detection (Turnstile, etc.)
- Session management and validation
- Portal-specific error detection
- Automatic recovery and fallback
"""

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from enum import Enum

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException,
    InvalidSessionIdException,
)

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


logger = logging.getLogger("gfh.audit.enhanced_scraper")


class AuthenticationState(Enum):
    """Portal authentication states"""
    UNAUTHENTICATED = "unauthenticated"
    AUTHENTICATING = "authenticating"
    AWAITING_2FA = "awaiting_2fa"
    AWAITING_VERIFICATION = "awaiting_verification"  # Turnstile, reCAPTCHA, etc.
    AUTHENTICATED = "authenticated"
    BLOCKED = "blocked"
    ERROR = "error"


class PortalAuthError(RuntimeError):
    """Portal authentication exception"""
    pass


class TurnstileDetected(PortalAuthError):
    """Cloudflare Turnstile challenge detected"""
    pass


class TwoFactorRequired(PortalAuthError):
    """2FA challenge detected"""
    pass


class HumanVerificationRequired(PortalAuthError):
    """Human verification required (general case)"""
    pass


class EnhancedPortalScraper(ABC):
    """
    Base scraper with robust authentication handling
    Incorporates patterns from GFH Audit Automation
    """
    
    portal_name = "portal"
    
    # Timeout configurations (in seconds)
    STANDARD_LOGIN_TIMEOUT = 20
    TWO_FACTOR_TIMEOUT = 120  # 2 minutes for 2FA
    VERIFICATION_TIMEOUT = 180  # 3 minutes for human verification
    PAGE_LOAD_TIMEOUT = 60
    
    # Retry configuration
    MAX_LOGIN_RETRIES = 3
    RETRY_DELAY_BASE = 2  # seconds (exponential backoff)
    
    # CSS/XPath selectors for common UI elements
    EMAIL_SELECTORS = [
        (By.CSS_SELECTOR, "input[type='email']"),
        (By.CSS_SELECTOR, "input[name='email']"),
        (By.CSS_SELECTOR, "input[autocomplete*='email']"),
        (By.XPATH, "//input[contains(@placeholder,'mail') or contains(@name,'mail')]"),
    ]
    
    PASSWORD_SELECTORS = [
        (By.CSS_SELECTOR, "input[type='password']"),
        (By.XPATH, "//input[contains(@placeholder,'assword') or contains(@name,'assword')]"),
    ]
    
    SUBMIT_SELECTORS = [
        (By.XPATH, "//button[contains(translate(text(),'LOGIN','login'),'login') or contains(.,'Sign in') or contains(.,'Log in')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, "input[type='submit']"),
    ]
    
    # 2FA Detection
    TWO_FA_INDICATORS = [
        (By.XPATH, "//*[contains(text(), '2-factor') or contains(text(), 'two-factor') or contains(text(), 'verification code')]"),
        (By.CSS_SELECTOR, "input[name*='code'], input[name*='otp'], input[name*='pin']"),
        (By.XPATH, "//label[contains(text(), 'Code') or contains(text(), 'OTP') or contains(text(), 'Verification')]"),
    ]
    
    # Human Verification Detection
    VERIFICATION_INDICATORS = [
        (By.CSS_SELECTOR, "iframe[src*='turnstile']"),  # Cloudflare Turnstile
        (By.CSS_SELECTOR, "iframe[src*='recaptcha']"),  # Google reCAPTCHA
        (By.XPATH, "//*[contains(text(), 'verify') or contains(text(), 'human') or contains(text(), 'challenge')]"),
        (By.CSS_SELECTOR, ".turnstile, .recaptcha, [class*='challenge']"),
    ]
    
    # Session blocked indicators
    BLOCKED_INDICATORS = [
        (By.XPATH, "//*[contains(text(), 'blocked') or contains(text(), 'suspended') or contains(text(), 'too many')]"),
        (By.CSS_SELECTOR, "[class*='error'], [class*='blocked'], [class*='denied']"),
    ]
    
    def __init__(
        self,
        driver_manager,
        email: str,
        password: str,
        profile_dir: Optional[Path] = None,
        login_timeout: int = STANDARD_LOGIN_TIMEOUT,
        twofa_timeout: int = TWO_FACTOR_TIMEOUT,
    ):
        """
        Initialize enhanced scraper
        
        Args:
            driver_manager: Selenium driver manager
            email: Portal email/username
            password: Portal password
            profile_dir: Browser profile directory (cookies persist here)
            login_timeout: Standard login timeout
            twofa_timeout: Extended timeout for 2FA
        """
        self.dm = driver_manager
        self.email = email
        self.password = password
        self.profile_dir = Path(profile_dir) if profile_dir else None
        self.login_timeout = login_timeout
        self.twofa_timeout = twofa_timeout
        self.auth_state = AuthenticationState.UNAUTHENTICATED
        self.login_attempts = 0
    
    # ===== Logging =====
    
    def log(self, message: str, level: str = "info") -> None:
        """Log with portal prefix"""
        msg = f"[{self.portal_name}] {message}"
        if level == "error":
            logger.error(msg)
        elif level == "warning":
            logger.warning(msg)
        elif level == "debug":
            logger.debug(msg)
        else:
            logger.info(msg)
    
    # ===== Element Finding (Robust) =====
    
    def _find_first(
        self,
        selectors: List[Tuple[By, str]],
        timeout: int = 8,
        raise_on_fail: bool = False
    ) -> Optional[object]:
        """
        Find first matching element from list of selectors
        Tries each selector in order, returns first match
        """
        for by, value in selectors:
            try:
                element = WebDriverWait(self.dm.driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
                return element
            except TimeoutException:
                continue
            except Exception as e:
                self.log(f"Selector error {by}={value}: {e}", "debug")
                continue
        
        if raise_on_fail:
            raise PortalAuthError(f"No element found from selectors: {selectors}")
        return None
    
    def _type(self, element, text: str) -> None:
        """Type text into element (robust)"""
        element.click()
        time.sleep(0.2)
        try:
            element.clear()
        except Exception:
            pass
        element.send_keys(text)
    
    # ===== Detection Methods =====
    
    def detect_auth_state(self) -> AuthenticationState:
        """Detect current authentication state"""
        try:
            # Check if already authenticated
            if self.is_authenticated():
                return AuthenticationState.AUTHENTICATED
            
            # Check for 2FA
            if self._find_first(self.TWO_FA_INDICATORS, timeout=2):
                self.log("2FA challenge detected", "warning")
                return AuthenticationState.AWAITING_2FA
            
            # Check for human verification (Turnstile, reCAPTCHA, etc.)
            if self._find_first(self.VERIFICATION_INDICATORS, timeout=2):
                self.log("Human verification challenge detected", "warning")
                return AuthenticationState.AWAITING_VERIFICATION
            
            # Check for blocked session
            if self._find_first(self.BLOCKED_INDICATORS, timeout=2):
                self.log("Session appears blocked", "error")
                return AuthenticationState.BLOCKED
            
            # Check if login form is visible
            if self._find_first(self.EMAIL_SELECTORS, timeout=2):
                return AuthenticationState.UNAUTHENTICATED
            
            return AuthenticationState.ERROR
            
        except Exception as e:
            self.log(f"Error detecting auth state: {e}", "debug")
            return AuthenticationState.ERROR
    
    def detect_turnstile(self) -> bool:
        """Specifically detect Cloudflare Turnstile"""
        try:
            iframe = self.dm.driver.find_element(By.CSS_SELECTOR, "iframe[src*='turnstile']")
            return bool(iframe)
        except NoSuchElementException:
            return False
    
    def detect_two_factor(self) -> bool:
        """Detect 2FA challenge"""
        try:
            return bool(self._find_first(self.TWO_FA_INDICATORS, timeout=2))
        except Exception:
            return False
    
    def detect_blocked_session(self) -> bool:
        """Detect if session is blocked"""
        try:
            return bool(self._find_first(self.BLOCKED_INDICATORS, timeout=2))
        except Exception:
            return False
    
    # ===== Authentication =====
    
    def login(self) -> bool:
        """
        Main login flow with retry logic
        Handles: standard login, 2FA, Turnstile, session blocks
        """
        if not self.email or not self.password:
            raise PortalAuthError(
                f"{self.portal_name} credentials not configured"
            )
        
        if not self.dm.is_valid and not self.dm.initialize():
            raise PortalAuthError("Browser driver initialization failed")
        
        # Retry loop
        for attempt in range(1, self.MAX_LOGIN_RETRIES + 1):
            self.login_attempts = attempt
            try:
                self.log(f"Login attempt {attempt}/{self.MAX_LOGIN_RETRIES}")
                return self._login_attempt()
            except TwoFactorRequired as e:
                self.log(f"2FA required: {e}", "warning")
                self._wait_for_2fa_completion()
                if self.is_authenticated():
                    self.log("2FA completed successfully")
                    return True
                raise PortalAuthError("2FA timed out")
            except TurnstileDetected as e:
                self.log(f"Turnstile detected: {e}", "warning")
                self._wait_for_turnstile_completion()
                if self.is_authenticated():
                    self.log("Turnstile completed successfully")
                    return True
                raise PortalAuthError("Turnstile timed out")
            except HumanVerificationRequired as e:
                self.log(f"Human verification required: {e}", "warning")
                self._wait_for_human_verification()
                if self.is_authenticated():
                    self.log("Human verification completed successfully")
                    return True
                raise PortalAuthError("Human verification timed out")
            except Exception as e:
                self.log(f"Login attempt {attempt} failed: {e}", "error")
                if attempt < self.MAX_LOGIN_RETRIES:
                    delay = self.RETRY_DELAY_BASE ** attempt
                    self.log(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    raise PortalAuthError(f"Login failed after {self.MAX_LOGIN_RETRIES} attempts")
        
        return False
    
    def _login_attempt(self) -> bool:
        """Single login attempt"""
        # Navigate to portal
        self.log(f"Navigating to {self.portal_url}")
        if not self.dm.navigate(self.portal_url, timeout=self.PAGE_LOAD_TIMEOUT):
            raise PortalAuthError(f"Could not open {self.portal_url}")
        
        time.sleep(2)
        
        # Check if already authenticated (from profile cookies)
        if self.is_authenticated():
            self.log("Already authenticated (from profile)")
            self.auth_state = AuthenticationState.AUTHENTICATED
            return True
        
        # Check current auth state
        state = self.detect_auth_state()
        self.auth_state = state
        
        if state == AuthenticationState.AWAITING_2FA:
            raise TwoFactorRequired("2FA challenge detected before login attempt")
        
        if state == AuthenticationState.AWAITING_VERIFICATION:
            raise TurnstileDetected("Human verification challenge detected")
        
        if state == AuthenticationState.BLOCKED:
            raise PortalAuthError("Session is blocked")
        
        # Fill in credentials
        email_field = self._find_first(self.EMAIL_SELECTORS, timeout=self.login_timeout)
        if email_field is None:
            if self.is_authenticated():
                return True
            raise PortalAuthError("Email input not found")
        
        self._type(email_field, self.email)
        self.log("Email entered")
        
        password_field = self._find_first(self.PASSWORD_SELECTORS, timeout=8)
        if password_field is None:
            raise PortalAuthError("Password input not found")
        
        self._type(password_field, self.password)
        self.log("Password entered")
        
        # Submit
        submit = self._find_first(self.SUBMIT_SELECTORS, timeout=5)
        if submit is not None:
            submit.click()
        else:
            password_field.send_keys(Keys.ENTER)
        
        self.log("Login submitted — waiting for response")
        
        # Wait for authentication or challenge
        deadline = time.time() + self.login_timeout + 10
        while time.time() < deadline:
            state = self.detect_auth_state()
            
            if state == AuthenticationState.AUTHENTICATED:
                self.log("Login successful")
                self.auth_state = AuthenticationState.AUTHENTICATED
                return True
            
            if state == AuthenticationState.AWAITING_2FA:
                raise TwoFactorRequired("2FA challenge appeared")
            
            if state == AuthenticationState.AWAITING_VERIFICATION:
                raise TurnstileDetected("Turnstile/verification appeared")
            
            if state == AuthenticationState.BLOCKED:
                raise PortalAuthError("Session blocked")
            
            time.sleep(1)
        
        raise PortalAuthError(
            f"Login did not complete within {self.login_timeout + 10}s"
        )
    
    def _wait_for_2fa_completion(self, timeout: Optional[int] = None) -> None:
        """Wait for user to complete 2FA"""
        timeout = timeout or self.twofa_timeout
        self.log(f"Waiting for 2FA completion (timeout: {timeout}s)")
        
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_authenticated():
                return
            
            state = self.detect_auth_state()
            if state == AuthenticationState.AUTHENTICATED:
                return
            
            time.sleep(2)
        
        raise TimeoutException(f"2FA not completed within {timeout}s")
    
    def _wait_for_turnstile_completion(self, timeout: Optional[int] = None) -> None:
        """Wait for Cloudflare Turnstile or similar verification"""
        timeout = timeout or self.VERIFICATION_TIMEOUT
        self.log(f"Waiting for Turnstile completion (timeout: {timeout}s)")
        
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_authenticated():
                return
            
            # Turnstile iframe disappears when solved
            if not self.detect_turnstile():
                # Re-check state after iframe disappears
                time.sleep(2)
                if self.is_authenticated():
                    return
            
            time.sleep(2)
        
        raise TimeoutException(f"Turnstile not completed within {timeout}s")
    
    def _wait_for_human_verification(self, timeout: Optional[int] = None) -> None:
        """Wait for human verification completion"""
        timeout = timeout or self.VERIFICATION_TIMEOUT
        self.log(f"Waiting for human verification (timeout: {timeout}s)")
        
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_authenticated():
                return
            
            state = self.detect_auth_state()
            if state == AuthenticationState.AUTHENTICATED:
                return
            
            time.sleep(2)
        
        raise TimeoutException(f"Human verification not completed within {timeout}s")
    
    # ===== Table Scraping (from GFH Automation) =====
    
    def scrape_tables_as_records(self, min_rows: int = 1) -> List[dict]:
        """
        Read visible HTML tables into list-of-dict records
        Uses BeautifulSoup for fast parsing, falls back to Selenium if needed
        """
        if BS4_AVAILABLE:
            try:
                html = self.dm.driver.page_source
                if html:
                    records = self._parse_tables_bs4(html, min_rows)
                    if records:
                        return records
            except Exception as e:
                self.log(f"BS4 parsing warning: {e}", "debug")
        
        return self._scrape_tables_selenium(min_rows)
    
    @staticmethod
    def _parse_tables_bs4(html: str, min_rows: int = 1) -> List[dict]:
        """Parse tables using BeautifulSoup"""
        soup = BeautifulSoup(html, "html.parser")
        records: List[dict] = []
        
        tables = soup.select("table")
        if not tables:
            tables = soup.select("div[role='table'], div[role='grid']")
        
        for table in tables:
            rows = table.select("tr")
            if not rows or len(rows) - 1 < min_rows:
                continue
            
            headers = [
                (cell.get_text(strip=True) or "Column")
                for cell in rows[0].select("th, td")
            ]
            if not headers:
                continue
            
            for row in rows[1:]:
                cells = row.select("td")
                if not cells:
                    continue
                
                record = {}
                for i, cell in enumerate(cells):
                    key = headers[i] if i < len(headers) else f"Column{i + 1}"
                    record[key] = cell.get_text(strip=True)
                
                if any(str(v).strip() for v in record.values()):
                    records.append(record)
        
        return records
    
    def _scrape_tables_selenium(self, min_rows: int = 1) -> List[dict]:
        """Fall back to Selenium DOM traversal"""
        records: List[dict] = []
        try:
            tables = self.dm.driver.find_elements(By.CSS_SELECTOR, "table")
            for table in tables:
                rows = table.find_elements(By.CSS_SELECTOR, "tr")
                if len(rows) - 1 < min_rows:
                    continue
                
                headers = []
                for cell in rows[0].find_elements(By.CSS_SELECTOR, "th, td"):
                    headers.append((cell.text or "").strip() or "Column")
                
                if not headers:
                    continue
                
                for row in rows[1:]:
                    cells = row.find_elements(By.CSS_SELECTOR, "td")
                    if not cells:
                        continue
                    
                    record = {}
                    for i, cell in enumerate(cells):
                        key = headers[i] if i < len(headers) else f"Column{i + 1}"
                        record[key] = (cell.text or "").strip()
                    
                    if any(str(v).strip() for v in record.values()):
                        records.append(record)
        
        except Exception as e:
            logger.warning(f"Table scraping failed: {e}")
        
        return records
    
    def try_download_buttons(
        self,
        keywords: List[str],
        download_dir: Path,
        wait_seconds: int = 25
    ) -> Optional[Path]:
        """
        Click download/export button matching keywords
        Waits for file to appear in download directory
        """
        before = set(download_dir.glob("*")) if download_dir.exists() else set()
        
        xpath_parts = []
        for keyword in keywords:
            xpath_parts.append(
                f"contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')"
            )
        
        xpath = "//button[" + " or ".join(xpath_parts) + "] | //a[" + " or ".join(xpath_parts) + "]"
        
        try:
            buttons = self.dm.driver.find_elements(By.XPATH, xpath)
            for button in buttons[:5]:
                try:
                    if button.is_displayed():
                        self.log(f"Clicking button: {(button.text or '')[:40]!r}")
                        button.click()
                        break
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Download button search failed: {e}")
            return None
        
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            time.sleep(1)
            if not download_dir.exists():
                continue
            
            new_files = {
                f for f in download_dir.glob("*")
                if f not in before and not f.name.endswith((".crdownload", ".tmp", ".part"))
            }
            
            if new_files:
                newest = max(new_files, key=lambda f: f.stat().st_mtime)
                self.log(f"Download completed: {newest.name}")
                return newest
        
        return None
    
    # ===== Abstract Methods =====
    
    @property
    @abstractmethod
    def portal_url(self) -> str:
        """Portal URL"""
        pass
    
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if authenticated"""
        pass
