#!/usr/bin/env python3
"""
GFH Timesheet Scraper - BeautifulSoup Automation

Extracts employee timesheet data from GFH Telecom timesheet app.

Usage:
    from gfh_timesheet_scraper import scrape_gfh_timesheet
    success, msg, filepath = scrape_gfh_timesheet(
        email="user@example.com",
        password="password"
    )

Returns XLSX with columns:
    - Employee
    - Store
    - Date
    - Clock In
    - Clock Out
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
except ImportError:
    raise ImportError("Required: pip install requests beautifulsoup4 pandas openpyxl")

logger = logging.getLogger(__name__)


class GFHTimesheetScraper:
    """GFH Timesheet scraper"""
    
    BASE_URL = "https://timesheet.gfhtelecoms.com"  # TODO: Confirm actual URL
    
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0'
        })
        self.authenticated = False
    
    def login(self) -> bool:
        """Authenticate with timesheet app"""
        try:
            logger.info(f"Logging in as {self.email}...")
            
            # Get login page
            login_url = f"{self.BASE_URL}/login"
            resp = self.session.get(login_url, timeout=15)
            
            if resp.status_code != 200:
                logger.error(f"Login page error: {resp.status_code}")
                return False
            
            # Parse for CSRF token if needed
            soup = BeautifulSoup(resp.content, 'html.parser')
            csrf_token = None
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input and csrf_input.get('value'):
                csrf_token = csrf_input['value']
            
            # POST login
            login_data = {
                'email': self.email,
                'password': self.password,
            }
            if csrf_token:
                login_data['csrf_token'] = csrf_token
            
            auth_resp = self.session.post(
                login_url,
                data=login_data,
                timeout=15,
                allow_redirects=True
            )
            
            # Verify login success
            if 'error' in auth_resp.text.lower() or 'invalid' in auth_resp.text.lower():
                logger.error("Login failed - invalid credentials")
                return False
            
            self.authenticated = True
            logger.info("✓ Login successful")
            return True
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    def fetch_timesheet_data(self) -> Optional[List[Dict]]:
        """Fetch timesheet records"""
        try:
            if not self.authenticated:
                logger.error("Not authenticated")
                return None
            
            logger.info("Fetching timesheet records...")
            
            # Try API endpoint first
            api_urls = [
                f"{self.BASE_URL}/api/timesheet",
                f"{self.BASE_URL}/api/employee/timesheet",
                f"{self.BASE_URL}/employee/timesheet",
            ]
            
            for url in api_urls:
                try:
                    resp = self.session.get(url, timeout=15)
                    
                    if resp.status_code == 200:
                        # Try JSON
                        try:
                            data = resp.json()
                            if isinstance(data, list) and len(data) > 0:
                                logger.info(f"✓ Fetched {len(data)} records from {url}")
                                return data
                        except:
                            pass
                        
                        # Try HTML parsing
                        soup = BeautifulSoup(resp.content, 'html.parser')
                        records = self._parse_timesheet_html(soup)
                        if records:
                            logger.info(f"✓ Parsed {len(records)} records from {url}")
                            return records
                except:
                    continue
            
            logger.warning("Could not fetch timesheet data")
            return None
            
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            return None
    
    def _parse_timesheet_html(self, soup: BeautifulSoup) -> Optional[List[Dict]]:
        """Parse timesheet table from HTML"""
        try:
            records = []
            
            # Find timesheet table
            table = soup.find('table', {'class': ['timesheet', 'data-table', 'table']})
            if not table:
                # Try finding by any table with relevant headers
                tables = soup.find_all('table')
                for t in tables:
                    headers = [th.text.strip().lower() for th in t.find_all('th')]
                    if any(x in ' '.join(headers) for x in ['employee', 'date', 'clock']):
                        table = t
                        break
            
            if not table:
                logger.warning("Timesheet table not found")
                return None
            
            # Parse rows
            rows = table.find_all('tr')[1:]  # Skip header row
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    record = {
                        'employee': cols[0].text.strip(),
                        'store': cols[1].text.strip() if len(cols) > 1 else '',
                        'date': cols[2].text.strip() if len(cols) > 2 else '',
                        'clock_in': cols[3].text.strip() if len(cols) > 3 else '',
                        'clock_out': cols[4].text.strip() if len(cols) > 4 else '',
                    }
                    if record['employee']:  # Only add if employee name exists
                        records.append(record)
            
            return records if records else None
            
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None
    
    def export_to_excel(self, records: List[Dict]) -> Optional[str]:
        """Export records to Excel"""
        try:
            logger.info(f"Exporting {len(records)} records to Excel...")
            
            df = pd.DataFrame(records)
            
            # Ensure required columns
            for col in ['employee', 'store', 'date', 'clock_in', 'clock_out']:
                if col not in df.columns:
                    df[col] = ''
            
            # Reorder and select columns
            df = df[['employee', 'store', 'date', 'clock_in', 'clock_out']]
            
            # Save to temp file
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = Path(temp_dir) / f"GFH_Timesheet_{timestamp}.xlsx"
            
            df.to_excel(output_file, sheet_name="Timesheet", index=False)
            
            logger.info(f"✓ Excel saved: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Excel export error: {e}")
            return None
    
    def scrape(self) -> Tuple[bool, str, Optional[str]]:
        """Execute full scrape"""
        try:
            if not self.login():
                return False, "Login failed", None
            
            records = self.fetch_timesheet_data()
            if not records:
                return False, "No timesheet data found", None
            
            filepath = self.export_to_excel(records)
            if filepath:
                return True, f"Exported {len(records)} records", filepath
            else:
                return False, "Export failed", None
                
        except Exception as e:
            logger.exception(f"Scrape failed: {e}")
            return False, str(e), None
        finally:
            self.session.close()


def scrape_gfh_timesheet(email: str, password: str) -> Tuple[bool, str, Optional[str]]:
    """Scrape GFH timesheet - returns (success, message, filepath)"""
    scraper = GFHTimesheetScraper(email, password)
    return scraper.scrape()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test: python gfh_timesheet_scraper.py
    success, msg, path = scrape_gfh_timesheet("user@example.com", "password")
    print(f"Success: {success}\nMessage: {msg}\nPath: {path}")
