"""
Database Manager - Extended schema for Inventory Audit with 6 tabs
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path.home() / "AppData" / "Local" / "B2BSoft_Inventory_Audit" / "data.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.init_database()
        
    def init_database(self):
        """Initialize database tables for all 6 tabs"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=10000")
            
            cursor = conn.cursor()
            
            # 1. Credentials table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS credentials (
                    id INTEGER PRIMARY KEY,
                    access_code TEXT,
                    account_id TEXT,
                    username TEXT,
                    password TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 2. Timesheet data (from B2B Soft scraping)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS timesheet_data (
                    id INTEGER PRIMARY KEY,
                    store TEXT,
                    district TEXT,
                    employee TEXT,
                    clock_in TEXT,
                    clock_out TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 3. Inventory Status (from scraping)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_status (
                    id INTEGER PRIMARY KEY,
                    store TEXT,
                    district TEXT,
                    count_status TEXT,
                    employees TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 4. Store List (Tab 3)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS store_list (
                    id INTEGER PRIMARY KEY,
                    district TEXT,
                    store TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 5. Employees (Tab 4)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY,
                    employee_name TEXT UNIQUE,
                    phone TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 6. Variance data (Tab 2)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS variance_data (
                    id INTEGER PRIMARY KEY,
                    district TEXT,
                    store TEXT,
                    product TEXT,
                    imei TEXT,
                    status TEXT,
                    rep_name TEXT,
                    clearance TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 7. District WhatsApp Groups (Tab 5)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS district_whatsapp_groups (
                    id INTEGER PRIMARY KEY,
                    district TEXT UNIQUE,
                    group_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 8. District DMs (Tab 5)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS district_dms (
                    id INTEGER PRIMARY KEY,
                    district TEXT,
                    dm_name TEXT,
                    phone TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 9. Excluded Devices (Tab 6)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS excluded_devices (
                    id INTEGER PRIMARY KEY,
                    district TEXT,
                    product TEXT,
                    imei TEXT,
                    comments TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 10. Inventory Audit Status (Tab 1)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_audit_status (
                    id INTEGER PRIMARY KEY,
                    district TEXT,
                    store TEXT,
                    status TEXT,
                    rep_name TEXT,
                    checkbox BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timesheet_store ON timesheet_data(store)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_store ON inventory_status(store)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_employees_name ON employees(employee_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_variance_store ON variance_data(store)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_excluded_imei ON excluded_devices(imei)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_store ON inventory_audit_status(store)")
            
            conn.commit()
            
    def store_timesheet_data(self, data):
        """Store timesheet data in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout=10000")
            cursor = conn.cursor()
            
            # Clear old data
            cursor.execute("DELETE FROM timesheet_data")
            
            # Insert new data
            for record in data:
                cursor.execute("""
                    INSERT INTO timesheet_data 
                    (store, district, employee, clock_in, clock_out, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    record.get("store", ""),
                    record.get("district", ""),
                    record.get("employee", ""),
                    record.get("clock_in", ""),
                    record.get("clock_out", ""),
                    record.get("status", "")
                ))
            
            conn.commit()
            
    def store_inventory_data(self, data):
        """Store inventory status data in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout=10000")
            cursor = conn.cursor()
            
            # Clear old data
            cursor.execute("DELETE FROM inventory_status")
            
            # Insert new data
            for record in data:
                employees_json = json.dumps(record.get("employees", []))
                cursor.execute("""
                    INSERT INTO inventory_status 
                    (store, district, count_status, employees)
                    VALUES (?, ?, ?, ?)
                """, (
                    record.get("store", ""),
                    record.get("district", ""),
                    record.get("count_status", "Pending"),
                    employees_json
                ))
            
            conn.commit()
            
    def add_employee(self, employee_name, phone="", created_by=""):
        """Add or update employee"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout=10000")
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO employees (employee_name, phone, created_by)
                    VALUES (?, ?, ?)
                """, (employee_name, phone, created_by))
            except sqlite3.IntegrityError:
                # Update if exists
                cursor.execute("""
                    UPDATE employees 
                    SET phone = ?, created_by = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE employee_name = ?
                """, (phone, created_by, employee_name))
            
            conn.commit()
            
    def add_store(self, district, store):
        """Add store to store list"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout=10000")
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO store_list (district, store)
                VALUES (?, ?)
            """, (district, store))
            
            conn.commit()
            
    def add_excluded_device(self, district, product, imei, comments=""):
        """Add excluded device"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout=10000")
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO excluded_devices (district, product, imei, comments)
                VALUES (?, ?, ?, ?)
            """, (district, product, imei, comments))
            
            conn.commit()
            
    def set_whatsapp_group(self, district, group_name):
        """Set WhatsApp group name for district"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout=10000")
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO district_whatsapp_groups (district, group_name)
                    VALUES (?, ?)
                """, (district, group_name))
            except sqlite3.IntegrityError:
                cursor.execute("""
                    UPDATE district_whatsapp_groups 
                    SET group_name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE district = ?
                """, (group_name, district))
            
            conn.commit()
            
    def set_district_dm(self, district, dm_name, phone):
        """Set DM for district"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout=10000")
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO district_dms (district, dm_name, phone)
                VALUES (?, ?, ?)
            """, (district, dm_name, phone))
            
            conn.commit()
            
    def get_employees(self):
        """Get all employees"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM employees ORDER BY employee_name")
            return [dict(row) for row in cursor.fetchall()]
            
    def get_stores(self):
        """Get all stores"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM store_list ORDER BY district, store")
            return [dict(row) for row in cursor.fetchall()]
            
    def get_timesheet_data(self):
        """Retrieve timesheet data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM timesheet_data ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
            
    def get_employees_by_store(self, store):
        """Get employees for specific store from timesheet"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT employee FROM timesheet_data WHERE store = ? AND employee IS NOT NULL",
                (store,)
            )
            return [row[0] for row in cursor.fetchall()]
            
    def backup_database(self):
        """Create backup of database"""
        import shutil
        backup_path = self.db_path.parent / f"data.bak.sqlite3"
        shutil.copy2(self.db_path, backup_path)
        return backup_path
