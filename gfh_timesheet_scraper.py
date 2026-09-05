#!/usr/bin/env python3
"""
GFH Timesheet App Scraper

Extracts employee shift/timesheet data from GFH Telecom timesheet app.

Usage:
  scraper = GFHTimesheetScraper(email, password)
  success, message, filepath = scraper.scrape()
  
Returns XLSX file with columns:
  - Employee (from "Employee" field)
  - Store (inferred from duty location)
  - Date
  - Clock In
  - Clock Out
  - District
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from datetime import datetime
import time

try:
    import requests
    from bs4 import BeautifulSoup
    import pandas as pd
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("Install: pip install requests beautifulsoup4 pandas openpyxl")
    exit(1)

logger = logging.getLogger(__name__)


class GFHTimesheetScraper:
    """GFH Telecom timesheet app scraper"""
    
    BASE_URL = "https://timesheet.gfhtelecoms.com"  # TODO: Confirm actual URL
    
    def __init__(self, email: str, password: str):
        """
        Initialize timesheet scraper
        
        Args:
            email: Login email address
            password: Login password
        """
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0'
        })
        
    def _login(self) -> bool:
        """Authenticate with GFH timesheet app"""
        try:
            logger.info("Authenticating with GFH timesheet app...")
            
            # Step 1: Get login page (CSRF token if needed)
            login_url = f"{self.BASE_URL}/login"
            resp = self.session.get(login_url, timeout=20)
            
            if resp.status_code != 200:
                logger.error(f"Failed to access login page: {resp.status_code}")
                return False
            
            # Step 2: Parse for CSRF token if present
            soup = BeautifulSoup(resp.content, 'html.parser')
            csrf_token = None
            
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input and csrf_input.get('value'):
                csrf_token = csrf_input['value']
                logger.debug(f"CSRF token found: {csrf_token[:20]}...")
            
            # Step 3: POST login credentials
            login_data = {
                'email': self.email,
                'password': self.password,
            }
            
            if csrf_token:
                login_data['csrf_token'] = csrf_token
            
            auth_resp = self.session.post(
                login_url,
                data=login_data,
                timeout=20,
                allow_redirects=True
            )
            
            # Step 4: Verify success (check for dashboard or error message)
            if 'dashboard' in auth_resp.url.lower() or 'employee' in auth_resp.text.lower():
                logger.info("✓ Authentication successful")
                return True
            elif 'error' in auth_resp.text.lower() or 'invalid' in auth_resp.text.lower():
                logger.error("Authentication failed: Invalid credentials")
                return False
            else:
                logger.info("Authentication completed (status unclear, proceeding)")
                return True
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def _fetch_timesheet_data(self) -> Optional[List[Dict]]:
        """Fetch timesheet records from dashboard"""
        try:
            logger.info("Fetching timesheet records...")
            
            # Endpoint for timesheet data (may vary based on actual app structure)
            url = f"{self.BASE_URL}/api/timesheet" or f"{self.BASE_URL}/employee/timesheet"
            
            resp = self.session.get(url, timeout=20)
            
            if resp.status_code != 200:
                logger.error(f"Failed to fetch timesheet: {resp.status_code}")
                return None
            
            # Try JSON first (API endpoint)
            try:
                data = resp.json()
                if isinstance(data, list):
                    logger.info(f"Fetched {len(data)} timesheet records (JSON)")
                    return data
            except:
                pass
            
            # Fall back to HTML parsing
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Parse table rows (structure may vary)
            records = []
            rows = soup.find_all('tr', class_='timesheet-row') or soup.find_all('tr')[1:]
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    record = {
                        'employee': (cols[0].text.strip() if len(cols) > 0 else ""),
                        'date': (cols[1].text.strip() if len(cols) > 1 else ""),
                        'clock_in': (cols[2].text.strip() if len(cols) > 2 else ""),
                        'clock_out': (cols[3].text.strip() if len(cols) > 3 else ""),
                        'store': (cols[4].text.strip() if len(cols) > 4 else ""),
                    }
                    records.append(record)
            
            logger.info(f"Parsed {len(records)} records from HTML")
            return records if records else None
            
        except Exception as e:
            logger.error(f"Failed to fetch timesheet data: {e}")
            return None
    
    def _parse_and_save_to_excel(self, records: List[Dict]) -> Optional[str]:
        """Convert records to Excel file"""
        try:
            logger.info(f"Converting {len(records)} records to Excel...")
            
            # Convert to DataFrame
            df = pd.DataFrame(records)
            
            # Ensure required columns
            required_cols = ['employee', 'date', 'clock_in', 'store']
            for col in required_cols:
                if col not in df.columns:
                    df[col] = ""
            
            # Reorder columns
            df = df[['employee', 'store', 'date', 'clock_in', 'clock_out']]
            
            # Add district column (empty for now, to be filled by audit workflow)
            df['district'] = ""
            
            # Save to temp file
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = Path(temp_dir) / f"GFH_Timesheet_{timestamp}.xlsx"
            
            df.to_excel(output_file, sheet_name="Timesheet", index=False)
            
            logger.info(f"✓ Excel file saved: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Failed to save Excel: {e}")
            return None
    
    def scrape(self) -> Tuple[bool, str, Optional[str]]:
        """
        Execute full scrape: login → fetch → export
        
        Returns:
            (success, message, filepath_or_none)
        """
        try:
            # Step 1: Login
            if not self._login():
                return False, "Authentication failed", None
            
            # Step 2: Fetch data
            records = self._fetch_timesheet_data()
            if not records:
                return False, "No timesheet records found", None
            
            # Step 3: Save to Excel
            filepath = self._parse_and_save_to_excel(records)
            if not filepath:
                return False, "Failed to save Excel file", None
            
            logger.info(f"✓ GFH Timesheet scrape complete: {filepath}")
            return True, f"Exported {len(records)} records", filepath
            
        except Exception as e:
            logger.exception(f"Scrape failed: {e}")
            return False, f"Scrape error: {str(e)}", None
        finally:
            self.session.close()


def scrape_gfh_timesheet(email: str, password: str) -> Tuple[bool, str, Optional[str]]:
    """
    Convenience function for GFH timesheet scraping
    
    Usage in DataExtractionWorker:
        success, msg, filepath = scrape_gfh_timesheet(email, password)
        if success:
            task_queue.put({'type': 'auto_import', 'timesheet_file': filepath})
    """
    scraper = GFHTimesheetScraper(email, password)
    return scraper.scrape()


# Developed by Abad Umair Channa | Copyright © 2026 | All rights reserved.
