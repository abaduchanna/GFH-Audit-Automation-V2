#!/usr/bin/env python3
"""
B2B Soft Portal Scraper

Specialized scraper for B2B Soft inventory count export.

Portal: https://wsreports.b2bsoft.com
Flow:
  1. Login: Company ID (9909129) → Account ID → Username/Password → 2FA
  2. Navigate to "Inventory Count Result Details"
  3. Select date range (Today)
  4. Export to XLSX
  5. Save to temp file

Returns filepath for auto-import.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions

logger = logging.getLogger(__name__)


class B2BSoftScraper:
    """B2B Soft portal scraper for inventory count export"""
    
    PORTAL_URL = "https://wsreports.b2bsoft.com"
    COMPANY_ID = "9909129"  # GFH Telecom fixed ID
    
    def __init__(self, access_code: str, account_id: str, username: str, password: str):
        """
        Initialize B2B Soft scraper
        
        Args:
            access_code: Company access code (e.g., "9909129")
            account_id: Numeric account ID (6 digits max)
            username: Portal username
            password: Portal password
        """
        self.access_code = access_code
        self.account_id = account_id
        self.username = username
        self.password = password
        self.driver = None
        self.wait = None
        
    def _init_driver(self) -> bool:
        """Initialize Selenium Chrome driver with Edge"""
        try:
            options = ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            
            # Headless mode
            options.add_argument('--headless')
            
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 20)
            
            logger.info("Chrome driver initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize driver: {e}")
            return False
            
    def _close_driver(self):
        """Close Selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def _login_step1_company_id(self) -> bool:
        """Step 1: Enter company ID and proceed"""
        try:
            logger.info("Step 1: Entering company ID...")
            self.driver.get(self.PORTAL_URL + "/#")
            
            # Wait for company ID field
            company_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "companyId"))
            )
            
            company_field.clear()
            company_field.send_keys(self.access_code)
            
            # Click submit
            submit_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, "btnSubmit"))
            )
            submit_btn.click()
            
            logger.info("Company ID submitted")
            return True
            
        except Exception as e:
            logger.error(f"Step 1 failed: {e}")
            return False
    
    def _login_step2_account_id(self) -> bool:
        """Step 2: Enter account ID"""
        try:
            logger.info("Step 2: Entering account ID...")
            
            account_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "AccountId"))
            )
            
            account_field.clear()
            account_field.send_keys(self.account_id)
            
            # Click next button (might be implicit or explicit)
            logger.info("Account ID entered")
            return True
            
        except Exception as e:
            logger.error(f"Step 2 failed: {e}")
            return False
    
    def _login_step3_credentials(self) -> bool:
        """Step 3: Enter username and password"""
        try:
            logger.info("Step 3: Entering credentials...")
            
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "Username"))
            )
            password_field = self.driver.find_element(By.ID, "Password")
            
            username_field.clear()
            username_field.send_keys(self.username)
            
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Click login button
            login_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, "btnClick"))
            )
            login_btn.click()
            
            logger.info("Credentials submitted")
            return True
            
        except Exception as e:
            logger.error(f"Step 3 failed: {e}")
            return False
    
    def _handle_2fa(self) -> bool:
        """Handle 2FA if presented"""
        try:
            # Check for 2FA screen
            self.wait.until(EC.presence_of_element_located((By.ID, "trustRadio")))
            
            logger.info("2FA detected - clicking trust device...")
            trust_radio = self.driver.find_element(By.ID, "trustRadio")
            trust_radio.click()
            
            # Click setup next button
            next_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, "setupNextBtn"))
            )
            next_btn.click()
            
            logger.info("2FA handled")
            return True
            
        except Exception as e:
            # 2FA might not be present
            logger.debug(f"No 2FA or already handled: {e}")
            return True
    
    def _navigate_to_inventory_report(self) -> bool:
        """Navigate to Inventory Count Result Details report"""
        try:
            logger.info("Navigating to Inventory Count Result Details...")
            
            # Wait for page to load after login
            self.wait.until(EC.presence_of_element_located((By.ID, "mainContent")))
            
            # Click tree node for Inventory Count Result Details
            # Selector: tree node with specific uniq attribute
            tree_item = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[uniq='9-212318']"))
            )
            tree_item.click()
            
            logger.info("Clicked Inventory Count Result Details")
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def _select_date_range(self) -> bool:
        """Select 'Today' date range"""
        try:
            logger.info("Selecting 'Today' date range...")
            
            # Click date picker for "Today"
            today_option = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-value='2']"))
            )
            today_option.click()
            
            logger.info("'Today' date range selected")
            return True
            
        except Exception as e:
            logger.error(f"Date range selection failed: {e}")
            return False
    
    def _export_to_excel(self, output_path: str) -> bool:
        """Trigger Excel export and wait for download"""
        try:
            logger.info(f"Exporting to Excel...")
            
            # Set download directory (headless mode)
            prefs = {
                'download.default_directory': str(Path(output_path).parent),
                'download.prompt_for_download': False,
            }
            
            # Execute export JS
            self.driver.execute_script(
                "window['Widget_12072'].WidgetPages.ExportReport('Xlsx', 1)"
            )
            
            logger.info("Export triggered")
            
            # Wait for file to appear
            import time
            max_wait = 60
            elapsed = 0
            
            while elapsed < max_wait:
                if Path(output_path).exists():
                    logger.info(f"Excel file ready at {output_path}")
                    return True
                time.sleep(2)
                elapsed += 2
            
            logger.error(f"Export timeout - file not found after {max_wait}s")
            return False
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def scrape(self) -> Tuple[bool, str, Optional[str]]:
        """
        Execute full scrape: login → navigate → export
        
        Returns:
            (success, message, filepath_or_none)
        """
        if not self._init_driver():
            return False, "Failed to initialize driver", None
        
        try:
            # Step 1: Company ID
            if not self._login_step1_company_id():
                return False, "Company ID login failed", None
            
            # Step 2: Account ID
            if not self._login_step2_account_id():
                return False, "Account ID login failed", None
            
            # Step 3: Credentials
            if not self._login_step3_credentials():
                return False, "Credential login failed", None
            
            # Step 4: Handle 2FA if present
            if not self._handle_2fa():
                return False, "2FA handling failed", None
            
            # Step 5: Navigate to inventory report
            if not self._navigate_to_inventory_report():
                return False, "Navigation to inventory report failed", None
            
            # Step 6: Select today's date
            if not self._select_date_range():
                return False, "Date range selection failed", None
            
            # Step 7: Export to Excel
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = Path(temp_dir) / f"B2B_Inventory_Count_{timestamp}.xlsx"
            
            if not self._export_to_excel(str(output_file)):
                return False, "Excel export failed", None
            
            logger.info(f"✓ B2B Soft scrape complete: {output_file}")
            return True, f"Exported to {output_file}", str(output_file)
            
        except Exception as e:
            logger.exception(f"Scrape failed: {e}")
            return False, f"Scrape error: {str(e)}", None
            
        finally:
            self._close_driver()


def scrape_b2b_inventory(
    access_code: str,
    account_id: str,
    username: str,
    password: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Convenience function for B2B scraping
    
    Usage in DataExtractionWorker:
        success, msg, filepath = scrape_b2b_inventory(
            access_code, account_id, username, password
        )
        if success:
            task_queue.put({'type': 'auto_import', 'b2b_file': filepath})
    """
    scraper = B2BSoftScraper(access_code, account_id, username, password)
    return scraper.scrape()


# Developed by Abad Umair Channa | Copyright © 2026 | All rights reserved.
