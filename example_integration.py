"""
Example Integration Code for B2B Soft Inventory Audit v2

Shows how to integrate the new enhanced modules:
  - enhanced_web_scraper_v2.py (2FA, Turnstile, timeouts)
  - whatsapp_window_manager_v2.py (window stability)

This is NOT production code — it's a reference showing integration patterns.

Copy/adapt these patterns into your actual V2 app.
"""

import tkinter as tk
from pathlib import Path
import time
import logging
from typing import List, Optional

# New modules from this integration
from enhanced_web_scraper_v2 import (
    EnhancedPortalScraper,
    TwoFactorRequired,
    TurnstileDetected,
    PortalAuthError,
    AuthenticationState,
)
from whatsapp_window_manager_v2 import WhatsAppWindowManager, context_focus_whatsapp


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== EXAMPLE 1: Create B2B Soft Scraper with Enhanced Auth =====

class B2BSoftScraper(EnhancedPortalScraper):
    """
    B2B Soft portal scraper with 2FA and Turnstile support
    
    Usage:
        scraper = B2BSoftScraper(
            driver_manager=dm,
            email="user@example.com",
            password="secret",
            profile_dir=Path.home() / "AppData" / "Local" / "B2BSoft_Audit"
        )
        
        if scraper.login():
            records = scraper.scrape_tables_as_records()
            print(f"Got {len(records)} records")
    """
    
    @property
    def portal_url(self) -> str:
        """B2B Soft portal URL"""
        return "https://wsreports.b2bsoft.com/#"
    
    def is_authenticated(self) -> bool:
        """
        Check if we're logged into B2B Soft
        
        B2B Soft shows password field when logged out,
        hides it when logged in.
        """
        try:
            from selenium.webdriver.common.by import By
            password_fields = self.dm.driver.find_elements(
                By.CSS_SELECTOR, "input[type='password']"
            )
            # If password field is NOT visible, we're logged in
            return len(password_fields) == 0
        except Exception:
            return False
    
    def get_count_details(self) -> List[dict]:
        """
        Scrape B2B Soft count details table
        
        Returns:
            List of dicts with columns:
            - Reconciliation #
            - Created Date
            - Store
            - Document Status
            - Product ID
            - Physical Qty
            - System Qty
            - Difference
            - etc.
        """
        records = self.scrape_tables_as_records(min_rows=5)
        if not records:
            raise PortalAuthError("No count details found in B2B Soft")
        return records


# ===== EXAMPLE 2: Login with 2FA/Turnstile Handling =====

def example_login_with_challenges(dm, email: str, password: str) -> Optional[B2BSoftScraper]:
    """
    Example login flow that handles 2FA and CAPTCHA challenges
    
    Args:
        dm: Selenium driver manager
        email: B2B Soft email
        password: B2B Soft password
        
    Returns:
        Authenticated scraper, or None if failed
    """
    
    scraper = B2BSoftScraper(
        driver_manager=dm,
        email=email,
        password=password,
        profile_dir=Path.home() / "AppData" / "Local" / "B2BSoft_Audit" / "browser_profile",
        login_timeout=20,
        twofa_timeout=120,
    )
    
    try:
        print("🔐 Logging in to B2B Soft...")
        scraper.login()
        print("✓ Login successful!")
        return scraper
        
    except TwoFactorRequired as e:
        print(f"⏳ 2FA Required: {e}")
        print("   Please enter your 2FA code when prompted...")
        print("   Waiting up to 2 minutes...")
        
        # System automatically waits for 2FA completion
        # This is handled inside scraper.login()
        if scraper.is_authenticated():
            print("✓ 2FA completed successfully!")
            return scraper
        else:
            print("✗ 2FA timed out or failed")
            return None
            
    except TurnstileDetected as e:
        print(f"⏳ CAPTCHA Challenge: {e}")
        print("   Please solve the Cloudflare Turnstile...")
        print("   Waiting up to 3 minutes...")
        
        # System automatically waits for CAPTCHA completion
        if scraper.is_authenticated():
            print("✓ CAPTCHA completed successfully!")
            return scraper
        else:
            print("✗ CAPTCHA timed out or failed")
            return None
            
    except PortalAuthError as e:
        print(f"✗ Login failed: {e}")
        return None


# ===== EXAMPLE 3: Retry Logic with Exponential Backoff =====

def example_login_with_retry(dm, email: str, password: str, max_attempts: int = 3):
    """
    Example showing automatic retry with exponential backoff
    
    The scraper already does this internally, but here's how you'd
    handle it in your calling code.
    """
    
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"\n📍 Attempt {attempt}/{max_attempts}")
            scraper = example_login_with_challenges(dm, email, password)
            
            if scraper and scraper.is_authenticated():
                print(f"✓ Logged in on attempt {attempt}")
                return scraper
            
        except Exception as e:
            print(f"✗ Attempt {attempt} failed: {e}")
            
            if attempt < max_attempts:
                delay = 2 ** attempt  # Exponential: 2s, 4s, 8s
                print(f"   Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"✗ All {max_attempts} attempts failed")
                return None
    
    return None


# ===== EXAMPLE 4: WhatsApp Sending with Window Stability =====

class AuditApp(tk.Tk):
    """
    Main audit app (simplified example)
    
    Shows how to:
    1. Login with enhanced scraper (handles 2FA/Turnstile)
    2. Send messages to WhatsApp with window stability (no shifting)
    """
    
    def __init__(self):
        super().__init__()
        self.title("B2B Soft Inventory Audit v2")
        self.geometry("1000x600")
        
        # Initialize WhatsApp window manager
        self.whatsapp_mgr = WhatsAppWindowManager(self, debug=True)
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self):
        """Create UI buttons"""
        
        # Status label
        self.status_label = tk.Label(self, text="Ready", font=("Segoe UI", 12))
        self.status_label.pack(pady=10)
        
        # Login button
        login_btn = tk.Button(
            self,
            text="Login & Load Data",
            command=self._on_login,
            font=("Segoe UI", 11),
            padx=10,
            pady=10,
        )
        login_btn.pack(pady=10)
        
        # Send to WhatsApp button
        send_btn = tk.Button(
            self,
            text="Send to WhatsApp",
            command=self._on_send,
            font=("Segoe UI", 11),
            padx=10,
            pady=10,
        )
        send_btn.pack(pady=10)
    
    def _on_login(self):
        """Login button clicked"""
        
        self.status_label.config(text="Logging in...")
        self.update()
        
        try:
            # This would be your actual driver manager
            # For now, just show the pattern
            scraper = example_login_with_challenges(
                dm=None,  # Use actual driver manager
                email="user@b2bsoft.com",
                password="password",
            )
            
            if scraper:
                self.scraper = scraper
                self.status_label.config(text="✓ Logged in successfully")
                
                # Load data
                self.status_label.config(text="Loading count details...")
                self.update()
                
                records = scraper.get_count_details()
                self.status_label.config(text=f"✓ Loaded {len(records)} records")
            else:
                self.status_label.config(text="✗ Login failed")
        
        except Exception as e:
            self.status_label.config(text=f"✗ Error: {e}")
            logger.error(f"Login error: {e}", exc_info=True)
    
    def _on_send(self):
        """Send button clicked"""
        
        if not hasattr(self, 'scraper'):
            self.status_label.config(text="✗ Please login first")
            return
        
        # Method A: Using context manager (recommended)
        self._send_with_context_manager()
        
        # Method B: Explicit focus/release (alternative)
        # self._send_explicit()
    
    def _send_with_context_manager(self):
        """Send message using context manager (cleanest)"""
        
        try:
            self.status_label.config(text="Sending to WhatsApp...")
            self.update()
            
            # Context manager automatically:
            # 1. Saves window geometry + state
            # 2. Focuses WhatsApp Desktop
            # 3. Sends message
            # 4. Restores window to exact position/state
            with self.whatsapp_mgr as manager:
                # WhatsApp is focused here
                
                # Simulate sending a message
                print("📱 Sending message to WhatsApp...")
                time.sleep(1)  # Simulate typing
                
                # In real code, you'd:
                # - Copy image to clipboard
                # - Paste to WhatsApp
                # - Type caption
                # - Send
            
            self.status_label.config(text="✓ Message sent (window restored)")
            
        except Exception as e:
            self.status_label.config(text=f"✗ Send failed: {e}")
            logger.error(f"Send error: {e}", exc_info=True)
    
    def _send_explicit(self):
        """Send message with explicit focus/release (alternative)"""
        
        try:
            self.status_label.config(text="Sending to WhatsApp...")
            self.update()
            
            # Save window state
            manager = WhatsAppWindowManager(self)
            if not manager.focus_whatsapp(auto_restore=False):
                raise Exception("Failed to focus WhatsApp")
            
            try:
                # WhatsApp is focused here
                print("📱 Sending message to WhatsApp...")
                time.sleep(1)  # Simulate sending
            
            finally:
                # Always restore, even if send fails
                manager.release_whatsapp_focus()
            
            self.status_label.config(text="✓ Message sent (window restored)")
            
        except Exception as e:
            self.status_label.config(text=f"✗ Send failed: {e}")
            logger.error(f"Send error: {e}", exc_info=True)


# ===== EXAMPLE 5: Scraping and Filtering =====

def example_scrape_and_filter(scraper: B2BSoftScraper, district: str) -> List[dict]:
    """
    Example showing how to scrape and filter records by district
    
    Args:
        scraper: Authenticated B2BSoftScraper
        district: District name (e.g., "Arizona", "Texas")
        
    Returns:
        Filtered records for that district
    """
    
    print(f"📊 Scraping count details for {district}...")
    
    # Scrape all records (fast with BeautifulSoup)
    all_records = scraper.get_count_details()
    print(f"   Got {len(all_records)} total records")
    
    # Filter by district
    district_records = [
        r for r in all_records
        if district.lower() in str(r.get("Store", "")).lower()
    ]
    
    print(f"   Filtered to {len(district_records)} records for {district}")
    return district_records


# ===== EXAMPLE 6: Profile Persistence =====

def example_profile_persistence():
    """
    Example showing browser profile persistence
    
    Cookies survive across app restarts — users don't need to log in again.
    """
    
    from selenium import webdriver
    
    profile_dir = Path.home() / "AppData" / "Local" / "B2BSoft_Audit" / "browser_profile"
    
    # First run: Create profile with logged-in state
    print("🔄 First run: Logging in...")
    driver = webdriver.Edge(user_data_dir=str(profile_dir))
    
    # ... login logic (scraper.login()) ...
    # Cookies are saved in profile_dir automatically
    
    driver.quit()
    
    # Second run: Profile still has cookies
    print("🔄 Second run: Using cached cookies...")
    driver = webdriver.Edge(user_data_dir=str(profile_dir))
    
    # Check if still logged in
    driver.get("https://wsreports.b2bsoft.com/#")
    time.sleep(2)
    
    # If cookies work, we're already authenticated!
    # If not, login normally (scraper detects this and re-authenticates)
    
    driver.quit()


# ===== EXAMPLE 7: Error Handling =====

def example_error_handling(scraper: B2BSoftScraper):
    """
    Example showing how to handle different error types
    """
    
    try:
        # Try to scrape
        records = scraper.get_count_details()
        
    except PortalAuthError as e:
        # Specific: Authentication failed
        print(f"❌ Authentication error: {e}")
        print("   Try logging in again")
        
    except TwoFactorRequired as e:
        # Specific: 2FA needed
        print(f"❌ 2FA required: {e}")
        print("   Enter your 2FA code when prompted")
        
    except TurnstileDetected as e:
        # Specific: CAPTCHA challenge
        print(f"❌ CAPTCHA challenge: {e}")
        print("   Solve the Turnstile verification")
        
    except Exception as e:
        # Generic: Something else went wrong
        print(f"❌ Unexpected error: {e}")
        logger.error(f"Error: {e}", exc_info=True)


# ===== MAIN =====

if __name__ == "__main__":
    print(__doc__)
    print("\n" + "="*70)
    print("EXAMPLE INTEGRATION CODE")
    print("="*70)
    
    print("\n📌 This shows integration patterns for:")
    print("  1. Enhanced web scraper (2FA, Turnstile, timeouts)")
    print("  2. WhatsApp window stability (no shifting)")
    print("  3. Error handling and retries")
    print("  4. Profile persistence")
    
    print("\n✅ Copy/adapt these patterns into your V2 app:")
    print("  - web_scraper.py (create B2BSoftScraper class)")
    print("  - whatsapp_manager.py (use WhatsAppWindowManager)")
    print("  - B2BSoft_Inventory_Audit_v2.py (integrate into UI)")
    
    print("\n🚀 Quick start:")
    print("  1. Read INTEGRATION_CHECKLIST.md")
    print("  2. Copy patterns from this example file")
    print("  3. Test 2FA flow manually")
    print("  4. Test window stability visually")
    print("  5. Deploy!")
    
    # Uncomment to run the app:
    # app = AuditApp()
    # app.mainloop()

# Developed by Abad Umair Channa | Copyright © 2026 | All rights reserved.
