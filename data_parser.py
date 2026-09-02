"""
Data parser for B2B Soft and GFH Telecom data

Parses and normalizes scraped data from portals.
"""

import logging
from typing import List, Dict, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class DataParser:
    """Parser for portal data with normalization and filtering"""
    
    def __init__(self, debug: bool = False):
        """
        Initialize data parser
        
        Args:
            debug: Enable debug logging
        """
        self.debug = debug
        
        if debug:
            logger.setLevel(logging.DEBUG)
    
    @staticmethod
    def normalize_district(text: str) -> str:
        """
        Normalize district name for matching
        
        Args:
            text: District name
            
        Returns:
            Normalized name (lowercase, no spaces)
        """
        return text.lower().strip().replace(' ', '').replace('_', '')
    
    @staticmethod
    def normalize_store(text: str) -> str:
        """
        Normalize store name for matching
        
        Args:
            text: Store name
            
        Returns:
            Normalized name
        """
        return text.lower().strip()
    
    def parse_count_details(self, records: List[Dict]) -> List[Dict]:
        """
        Parse B2B Soft count detail records
        
        Args:
            records: Raw records from scraper
            
        Returns:
            Parsed records with normalized fields
        """
        if not records:
            logger.warning("No count detail records to parse")
            return []
        
        logger.info(f"Parsing {len(records)} count detail records")
        
        # Normalize and filter records
        parsed = []
        for record in records:
            try:
                # Skip summary rows
                if self._is_summary_row(record):
                    continue
                
                parsed_record = {
                    'reconciliation_num': record.get('Reconciliation #', ''),
                    'created_date': record.get('Created Date', ''),
                    'store': self.normalize_store(record.get('Store', '')),
                    'status': record.get('Document Status', ''),
                    'product_id': record.get('Product ID', ''),
                    'product_desc': record.get('Product Description', ''),
                    'physical_qty': self._parse_int(record.get('Physical Qty', 0)),
                    'system_qty': self._parse_int(record.get('System Qty', 0)),
                    'difference': self._parse_int(record.get('Difference', 0)),
                    'serial_num': record.get('Serial #', ''),
                }
                parsed.append(parsed_record)
            except Exception as e:
                logger.warning(f"Error parsing record: {e}")
                continue
        
        logger.info(f"Parsed {len(parsed)} valid records")
        return parsed
    
    def parse_timesheet_data(self, records: List[Dict]) -> List[Dict]:
        """
        Parse GFH Telecom timesheet records
        
        Args:
            records: Raw records from scraper
            
        Returns:
            Parsed records with normalized fields
        """
        if not records:
            logger.warning("No timesheet records to parse")
            return []
        
        logger.info(f"Parsing {len(records)} timesheet records")
        
        parsed = []
        for record in records:
            try:
                # Skip summary rows (rows starting with "—")
                if self._is_summary_row(record):
                    continue
                
                parsed_record = {
                    'employee': record.get('Employee', '').strip(),
                    'email': record.get('Email', '').strip(),
                    'district': self.normalize_district(record.get('District', '')),
                    'store': self.normalize_store(record.get('Store', '')),
                    'date': record.get('Date', ''),
                    'clock_in': record.get('Clock In', ''),
                    'clock_out': record.get('Clock Out', ''),
                    'hours_worked': self._parse_float(record.get('Hours Worked', 0)),
                    'status': record.get('Status', ''),
                }
                
                # Skip if missing required fields
                if not parsed_record['employee']:
                    continue
                
                parsed.append(parsed_record)
            except Exception as e:
                logger.warning(f"Error parsing timesheet record: {e}")
                continue
        
        logger.info(f"Parsed {len(parsed)} valid timesheet records")
        return parsed
    
    def filter_by_district(self, records: List[Dict], district: str) -> List[Dict]:
        """
        Filter records by district with fuzzy matching
        
        Args:
            records: Records to filter
            district: District name to match
            
        Returns:
            Filtered records
        """
        if not district:
            return records
        
        wanted = self.normalize_district(district)
        matched = []
        
        for record in records:
            # Try to match district field
            if 'district' in record:
                if wanted == self.normalize_district(record['district']):
                    matched.append(record)
            
            # Fallback: try store field
            elif 'store' in record:
                if wanted in self.normalize_store(record['store']):
                    matched.append(record)
        
        logger.info(f"Filtered {len(matched)} records for district: {district}")
        return matched
    
    @staticmethod
    def _is_summary_row(record: Dict) -> bool:
        """Check if record is a summary/total row"""
        for key, value in record.items():
            if isinstance(value, str):
                # Skip rows with "TOTAL" or starting with "—"
                if value.upper().startswith(('—', 'TOTAL')) or "TOTAL" in value.upper():
                    return True
        return False
    
    @staticmethod
    def _parse_int(value) -> int:
        """Parse value to int, return 0 if invalid"""
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0
    
    @staticmethod
    def _parse_float(value) -> float:
        """Parse value to float, return 0.0 if invalid"""
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


# Developed by Abad Umair Channa | Copyright © 2026 | All rights reserved.
