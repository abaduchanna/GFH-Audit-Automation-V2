#!/usr/bin/env python3
"""
B2B Soft Portal Scraper - Selenium Automation

Automates login and export from B2B Soft inventory portal.

Portal: https://wsreports.b2bsoft.com
Flow:
  1. Login: Company ID → Account ID → Username/Password → 2FA (if needed)
  2. Navigate to "Inventory Count Result Details"
  3. Export to XLSX
  4. Return filepath

Usage:
    from b2b_scraper import scrape_b2b_inventory
    success, msg, filepath = scrape_b2b_inventory(
        access_code="9909129",
        account_id="123456",
        username="user@example.com",
        password="password"
    )
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import time

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
except ImportError:
    raise ImportError("selenium required: pip install selenium")

logger = logging.getLogger(__name__)


class B2BSoftScraper:
    """B2B Soft portal automation"""
    
    PORTAL_URL = "https://wsreports.b2bsoft.com"
    
    def __init__(self, access_code: str, account_id: str, username: str, password: str):
        self.access_code = access_code
        self.account_id = account_id
        self.username = username
        self.password = password
        self.driver = None
        self.wait = None
        
    def _init_driver(self) -> bool:
        """Initialize Chrome WebDriver"""
        try:
            options = ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 20)
            logger.info("Chrome driver initialized")
            return True
        except Exception as e:
            logger.error(f"Driver init failed: {e}")
            return False
    
    def _close_driver(self):
        """Close WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def login(self) -> bool:
        """Login to B2B Soft portal"""
        try:
            logger.info("Logging in to B2B Soft...")
            self.driver.get(self.PORTAL_URL + "/#")
            
            # Step 1: Company ID
            company_field = self.wait.until(EC.presence_of_element_located((By.ID, "companyId")))
            company_field.send_keys(self.access_code)
            submit_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "btnSubmit")))
            submit_btn.click()
            time.sleep(2)
            
            # Step 2: Account ID
            account_field = self.wait.until(EC.presence_of_element_located((By.ID, "AccountId")))
            account_field.send_keys(self.account_id)
            time.sleep(1)
            
            # Step 3: Username & Password
            username_field = self.wait.until(EC.presence_of_element_located((By.ID, "Username")))
            password_field = self.driver.find_element(By.ID, "Password")
            username_field.send_keys(self.username)
            password_field.send_keys(self.password)
            
            login_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "btnClick")))
            login_btn.click()
            time.sleep(3)
            
            logger.info("✓ Login successful")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def navigate_to_report(self) -> bool:
        """Navigate to Inventory Count Result Details"""
        try:
            logger.info("Navigating to inventory report...")
            
            # Find and click the report in the tree menu
            try:
                tree_item = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[uniq='9-212318']"))
                )
                tree_item.click()
                time.sleep(2)
                logger.info("✓ Navigated to report")
                return True
            except:
                logger.warning("Report link not found, trying alternative...")
                # Fallback: look for any report link with "Count" in it
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                return True
                
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def export_xlsx(self) -> Optional[str]:
        """Export data to XLSX"""
        try:
            logger.info("Exporting to Excel...")
            
            # Set up download directory
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = Path(temp_dir) / f"B2B_Inventory_{timestamp}.xlsx"
            
            # Execute export (may vary based on portal version)
            try:
                export_btn = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='export-button']")
                export_btn.click()
            except:
                # Try JavaScript export
                self.driver.execute_script(
                    "window['Widget_12072'].WidgetPages.ExportReport('Xlsx', 1)" if 'Widget_12072' in self.driver.page_source else ""
                )
            
            # Wait for download
            for _ in range(30):
                # Look for any .xlsx file in temp directory
                xlsx_files = list(Path(temp_dir).glob("*.xlsx"))
                if xlsx_files:
                    latest = max(xlsx_files, key=lambda p: p.stat().st_mtime)
                    logger.info(f"✓ Export complete: {latest}")
                    return str(latest)
                time.sleep(1)
            
            logger.error("Export timeout")
            return None
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return None
    
    def scrape(self) -> Tuple[bool, str, Optional[str]]:
        """Execute full scrape"""
        if not self._init_driver():
            return False, "Failed to initialize driver", None
        
        try:
            if not self.login():
                return False, "Login failed", None
            
            if not self.navigate_to_report():
                return False, "Navigation failed", None
            
            filepath = self.export_xlsx()
            if filepath:
                return True, f"Exported to {Path(filepath).name}", filepath
            else:
                return False, "Export failed", None
                
        except Exception as e:
            logger.exception(f"Scrape failed: {e}")
            return False, str(e), None
        finally:
            self._close_driver()


def scrape_b2b_inventory(
    access_code: str,
    account_id: str,
    username: str,
    password: str
) -> Tuple[bool, str, Optional[str]]:
    """Scrape B2B Soft inventory - returns (success, message, filepath)"""
    scraper = B2BSoftScraper(access_code, account_id, username, password)
    return scraper.scrape()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test: python b2b_scraper.py
    success, msg, path = scrape_b2b_inventory("9909129", "123456", "user", "pass")
    print(f"Success: {success}\nMessage: {msg}\nPath: {path}")
