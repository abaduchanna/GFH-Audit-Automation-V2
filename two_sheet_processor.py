"""
Two-Sheet Processor for B2B Soft Inventory Audit V2

Orchestrates the complete flow:
1. Import B2B Soft count details Excel
2. Import GFH Telecom timesheet Excel
3. Process both sheets together
4. Generate audit status (Tab 1) and variances (Tab 2)
5. Save to database

Uses production-proven logic from GFH Audit Automation (Timesheet Edition)
"""

import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from two_sheet_logic import (
    build_store_maps,
    extract_variances,
    identify_pending_stores,
    normalize_store,
    normalize_district,
)

logger = logging.getLogger(__name__)


class TwoSheetProcessor:
    """Process count details + timesheet to generate audit data"""
    
    def __init__(self, db_manager=None):
        """
        Initialize processor
        
        Args:
            db_manager: DatabaseManager instance (optional, for saving results)
        """
        self.db_manager = db_manager
        self.count_records = []
        self.timesheet_records = []
        self.variances = []
        self.pending_stores = []
        self.metrics = {}
    
    def load_count_excel(self, filepath: str) -> Tuple[bool, str]:
        """
        Load B2B Soft count details from Excel
        
        Args:
            filepath: Path to Inventory_Count_Result_Details.xlsx
            
        Returns:
            (success, message)
        """
        try:
            df = pd.read_excel(filepath)
            self.count_records = df.to_dict('records')
            msg = f"Loaded {len(self.count_records)} count records from B2B Soft"
            logger.info(msg)
            return True, msg
        except Exception as e:
            msg = f"Failed to load count Excel: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def load_timesheet_excel(self, filepath: str) -> Tuple[bool, str]:
        """
        Load GFH Telecom timesheet from Excel
        
        Args:
            filepath: Path to timesheets_*.xlsx
            
        Returns:
            (success, message)
        """
        try:
            df = pd.read_excel(filepath)
            self.timesheet_records = df.to_dict('records')
            msg = f"Loaded {len(self.timesheet_records)} timesheet records from GFH Telecom"
            logger.info(msg)
            return True, msg
        except Exception as e:
            msg = f"Failed to load timesheet Excel: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def process(self) -> Tuple[bool, str]:
        """
        Process both sheets together
        
        Returns:
            (success, message)
        """
        if not self.count_records:
            return False, "Count records not loaded. Load B2B Soft Excel first."
        
        if not self.timesheet_records:
            return False, "Timesheet records not loaded. Load GFH Telecom Excel first."
        
        try:
            logger.info("Processing count + timesheet data...")
            
            # Extract variances
            self.variances, var_metrics = extract_variances(
                self.count_records,
                self.timesheet_records
            )
            
            # Identify pending stores
            self.pending_stores, pend_metrics = identify_pending_stores(
                self.count_records,
                self.timesheet_records
            )
            
            # Merge metrics
            self.metrics = {
                **var_metrics,
                **pend_metrics,
                "variances": len(self.variances),
                "pending_stores": len(self.pending_stores),
                "total_stores": pend_metrics["total_stores"],
            }
            
            msg = (
                f"Processed successfully:\n"
                f"  - {len(self.variances)} variances extracted\n"
                f"  - {len(self.pending_stores)} pending stores\n"
                f"  - {self.metrics['total_stores']} total stores"
            )
            logger.info(msg)
            return True, msg
            
        except Exception as e:
            msg = f"Processing failed: {str(e)}"
            logger.error(msg, exc_info=True)
            return False, msg
    
    def save_to_database(self) -> Tuple[bool, str]:
        """
        Save audit status and variances to database
        
        Returns:
            (success, message)
        """
        if not self.db_manager:
            return False, "Database manager not provided"
        
        if not self.variances and not self.pending_stores:
            return False, "No data to save. Run process() first."
        
        try:
            logger.info("Saving to database...")
            
            # Save completed stores (from variances)
            completed_stores = set()
            for variance in self.variances:
                store = variance["store"]
                district = variance.get("district", "Unknown")
                employee = variance.get("employee", "")
                
                completed_stores.add((store, district, employee))
                
                # Save variance
                self.db_manager.execute("""
                    INSERT INTO variance_data 
                    (store, district, employee, imei, product, status, created_by, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    store,
                    district,
                    employee,
                    variance["imei"],
                    variance["product"],
                    variance["status"],
                    variance.get("created_by", ""),
                    variance.get("created_date", ""),
                ))
            
            # Save pending stores
            for pending in self.pending_stores:
                self.db_manager.execute("""
                    INSERT INTO inventory_status
                    (store, district, employee, count_status, percentage_complete, last_updated)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    pending["store"],
                    pending["district"],
                    pending["employee"],
                    "Pending",
                    0,
                ))
            
            # Save completed stores
            for store, district, employee in completed_stores:
                self.db_manager.execute("""
                    INSERT OR REPLACE INTO inventory_status
                    (store, district, employee, count_status, percentage_complete, last_updated)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    store,
                    district,
                    employee,
                    "Completed",
                    100,
                ))
            
            msg = (
                f"Saved to database:\n"
                f"  - {len(self.variances)} variance rows\n"
                f"  - {len(self.pending_stores)} pending stores\n"
                f"  - {len(completed_stores)} completed stores"
            )
            logger.info(msg)
            return True, msg
            
        except Exception as e:
            msg = f"Database save failed: {str(e)}"
            logger.error(msg, exc_info=True)
            return False, msg
    
    def get_audit_status(self) -> List[Dict]:
        """
        Get audit status rows for Tab 1
        
        Combines pending + completed stores with employee names
        """
        audit_rows = []
        
        # Add pending stores
        for pending in self.pending_stores:
            audit_rows.append({
                "store": pending["store"],
                "district": pending["district"],
                "employee": pending["employee"],
                "status": "Pending",
                "percentage": "0%",
            })
        
        # Add completed stores (from variances)
        completed = {}
        for variance in self.variances:
            key = (variance["store"], variance["district"])
            if key not in completed:
                completed[key] = variance["employee"]
        
        for (store, district), employee in completed.items():
            audit_rows.append({
                "store": store,
                "district": district,
                "employee": employee,
                "status": "Completed",
                "percentage": "100%",
            })
        
        return audit_rows
    
    def get_variances(self) -> List[Dict]:
        """
        Get variance rows for Tab 2
        
        Filtered by status (exclude "Matched")
        """
        return [
            v for v in self.variances 
            if v["status"].lower() not in ["matched", "ok", "balanced"]
        ]
    
    def get_summary(self) -> Dict:
        """Get processing summary"""
        return {
            "status": "success" if self.variances or self.pending_stores else "empty",
            "total_stores": self.metrics.get("total_stores", 0),
            "completed_stores": len(set((v["store"] for v in self.variances))),
            "pending_stores": len(self.pending_stores),
            "variances": len(self.get_variances()),
            "metrics": self.metrics,
        }


# Convenience functions for V2 app

def process_both_sheets(
    count_file: str,
    timesheet_file: str,
    db_manager=None
) -> Tuple[bool, str, TwoSheetProcessor]:
    """
    Convenience function: load + process + save
    
    Usage in V2 app:
        success, message, processor = process_both_sheets(
            count_file,
            timesheet_file,
            self.db_manager
        )
        if success:
            self.processor = processor
            self.populate_tab1(processor.get_audit_status())
            self.populate_tab2(processor.get_variances())
    """
    processor = TwoSheetProcessor(db_manager)
    
    # Load count
    success, msg = processor.load_count_excel(count_file)
    if not success:
        return False, msg, processor
    
    # Load timesheet
    success, msg = processor.load_timesheet_excel(timesheet_file)
    if not success:
        return False, msg, processor
    
    # Process
    success, msg = processor.process()
    if not success:
        return False, msg, processor
    
    # Save to DB
    if db_manager:
        success, msg = processor.save_to_database()
        if not success:
            logger.warning(f"DB save failed but processing succeeded: {msg}")
    
    return True, msg, processor


# Developed by Abad Umair Channa | Copyright © 2026 | All rights reserved.
