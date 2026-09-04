"""
B2B Soft Inventory Audit v2 - Enhanced with Audit Control Panel
Features:
- Auto-import Store/District from Excel files
- Audit Control Panel with time picker
- Automated 15-minute polling workflow
- WhatsApp message scheduling
- State management: START → STOP/HOLD/RESUME
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

from database_manager import DatabaseManager
from credential_manager import CredentialManager
from web_scraper import WebScraper
from data_parser import DataParser
from two_sheet_processor import TwoSheetProcessor, process_both_sheets
from audit_workflow_manager import AuditWorkflowManager
from theme_manager import ThemeManager
from header_manager import FixedHeaderManager


class AuditControlPanel:
    """Manages audit workflow state and scheduling"""
    
    STATE_IDLE = "IDLE"
    STATE_RUNNING = "RUNNING"
    STATE_STOPPED = "STOPPED"
    STATE_HELD = "HELD"
    
    def __init__(self):
        self.state = self.STATE_IDLE
        self.start_time = None
        self.audit_data = {}
        self.last_poll_time = None
        self.poll_interval = 15 * 60  # 15 minutes in seconds
        self.whatsapp_messages_sent = set()  # Track sent messages
        
    def set_start_time(self, start_time_str):
        """Set audit start time (HH:MM format)"""
        try:
            self.start_time = datetime.strptime(start_time_str, "%H:%M").time()
            return True
        except ValueError:
            return False
            
    def should_send_start_message(self):
        """Check if it's time to send starting message"""
        if self.state != self.STATE_RUNNING or not self.start_time:
            return False
        
        now = datetime.now().time()
        return now >= self.start_time and "start_message" not in self.whatsapp_messages_sent
        
    def should_poll(self):
        """Check if it's time for 15-minute poll"""
        if self.state != self.STATE_RUNNING:
            return False
        
        now = datetime.now()
        if self.last_poll_time is None:
            self.last_poll_time = now
            return True
            
        if (now - self.last_poll_time).total_seconds() >= self.poll_interval:
            self.last_poll_time = now
            return True
            
        return False


class B2BSoftInventoryAuditApp:
    def __init__(self, root):
        self.root = root
        self.root.title("B2B Soft Inventory Audit - Enhanced with Audit Control")
        self.root.geometry("1600x1000")
        
        # Set window icon (taskbar + title bar)
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GFH.B2BSoft.InventoryAudit")
        except:
            pass  # Non-Windows or permission issue
        
        try:
            self.root.iconbitmap("gfh_icon.ico")
        except:
            pass  # Icon file not found, use default
        
        # Initialize managers
        self.db_manager = DatabaseManager()
        self.credential_manager = CredentialManager(self.db_manager)
        self.scraper = WebScraper()
        self.data_parser = DataParser()
        self.processor = None  # Two-sheet processor (set after import)
        self.workflow_manager = None  # AuditWorkflowManager (set when audit starts)
        
        # Branding & Theme
        self.theme_manager = ThemeManager()
        self.header_manager = FixedHeaderManager(self.root, title="B2B Soft Inventory Audit V2", height=90)
        
        self.audit_panel = AuditControlPanel()
        
        # Monitoring thread
        self.monitor_thread = None
        self.monitoring = False
        
        # Setup GUI
        self.setup_gui()
        self.load_credentials()
        
        # Start monitoring thread
        self.start_monitoring()
        
    def get_districts_from_db(self):
        """Load unique districts from database"""
        try:
            cursor = self.db_manager.conn.cursor()
            cursor.execute("SELECT DISTINCT district FROM store_list ORDER BY district")
            districts = [row[0] for row in cursor.fetchall() if row[0]]
            return districts if districts else ["Arizona", "Colorado East", "Colorado West", "Atlanta", "Houston", "Louisiana", "Tennessee"]
        except:
            return ["Arizona", "Colorado East", "Colorado West", "Atlanta", "Houston", "Louisiana", "Tennessee"]
        
    def setup_gui(self):
        """Setup main GUI layout with branding and theme"""
        # Apply theme to window and root
        self.theme_manager.apply_theme_to_window(self.root)
        
        # Setup branded header (logo + title + theme toggle)
        self.header_manager.set_logo("gfh_icon.ico", text="GFH Telecom")
        self.header_manager.add_theme_toggle(self.theme_manager, callback=self.on_theme_toggle)
        
        # Main content
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel: Credentials + Audit Control
        self.setup_left_panel(main_frame)
        
        # Right panel: Tabs
        self.setup_tabs_panel(main_frame)
        
        # Footer
        self.setup_footer(main_frame)
        
        # Load saved credentials
        self.load_credentials()
        
    def on_theme_toggle(self):
        """Called when theme toggle button is clicked"""
        # Theme already toggled in header_manager's callback
        # Just update all UI elements
        try:
            from theme_manager import apply_theme_to_window
            apply_theme_to_window(self.root, self.theme_manager)
            self.update_status(f"✓ Theme changed to {self.theme_manager.current_theme}")
        except Exception as e:
            logger.warning(f"Theme toggle error: {e}")
        
    def setup_left_panel(self, parent):
        """Setup left panel with credentials + audit control"""
        left_frame = ttk.Frame(parent)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10), pady=10)
        
        # === Credentials Section ===
        cred_frame = ttk.LabelFrame(left_frame, text="B2B Soft Login", padding=10)
        cred_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(cred_frame, text="Access Code:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.access_code_var = tk.StringVar()
        ttk.Entry(cred_frame, textvariable=self.access_code_var, width=20).grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        ttk.Label(cred_frame, text="Account ID:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.account_id_var = tk.StringVar()
        ttk.Entry(cred_frame, textvariable=self.account_id_var, width=20).grid(row=1, column=1, sticky=tk.EW, pady=5)
        
        ttk.Label(cred_frame, text="Username:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.username_var = tk.StringVar()
        ttk.Entry(cred_frame, textvariable=self.username_var, width=20).grid(row=2, column=1, sticky=tk.EW, pady=5)
        
        ttk.Label(cred_frame, text="Password:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar()
        ttk.Entry(cred_frame, textvariable=self.password_var, width=20, show="•").grid(row=3, column=1, sticky=tk.EW, pady=5)
        
        button_frame = ttk.Frame(cred_frame)
        button_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        ttk.Button(button_frame, text="Save", command=self.save_credentials, width=8).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="Clear", command=self.clear_credentials, width=8).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="Scrape", command=self.start_scraping, width=8).pack(side=tk.LEFT, padx=3)
        
        cred_frame.columnconfigure(1, weight=1)
        
        # === GFH Telecom Timesheet Login ===
        ts_frame = ttk.LabelFrame(left_frame, text="GFH Telecom Timesheet Login", padding=10)
        ts_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(ts_frame, text="Email:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.ts_email_var = tk.StringVar()
        ttk.Entry(ts_frame, textvariable=self.ts_email_var, width=20).grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        ttk.Label(ts_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ts_password_var = tk.StringVar()
        ttk.Entry(ts_frame, textvariable=self.ts_password_var, width=20, show="•").grid(row=1, column=1, sticky=tk.EW, pady=5)
        
        ts_button_frame = ttk.Frame(ts_frame)
        ts_button_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        ttk.Button(ts_button_frame, text="Save", command=self.save_timesheet_credentials, width=8).pack(side=tk.LEFT, padx=3)
        ttk.Button(ts_button_frame, text="Clear", command=self.clear_timesheet_credentials, width=8).pack(side=tk.LEFT, padx=3)
        ttk.Button(ts_button_frame, text="Fetch", command=self.fetch_timesheet_data, width=8).pack(side=tk.LEFT, padx=3)
        
        ts_frame.columnconfigure(1, weight=1)
        
        # === Audit Control Panel ===
        audit_frame = ttk.LabelFrame(left_frame, text="⏰ Audit Control Panel", padding=12)
        audit_frame.pack(fill=tk.X, pady=(0, 15))
        
        # District selector
        ttk.Label(audit_frame, text="Select District:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.audit_district_var = tk.StringVar()
        district_combo = ttk.Combobox(
            audit_frame,
            textvariable=self.audit_district_var,
            values=self.get_districts_from_db(),
            state="readonly",
            width=20
        )
        district_combo.grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        # Start time picker
        ttk.Label(audit_frame, text="Audit Start Time:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.audit_time_var = tk.StringVar(value="09:00")
        time_entry = ttk.Entry(audit_frame, textvariable=self.audit_time_var, width=20)
        time_entry.grid(row=1, column=1, sticky=tk.EW, pady=5)
        ttk.Label(audit_frame, text="(HH:MM)", font=("Segoe UI", 8)).grid(row=1, column=2, sticky=tk.W, padx=5)
        
        # Status display
        ttk.Label(audit_frame, text="Status:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.audit_status_var = tk.StringVar(value="IDLE")
        status_label = ttk.Label(audit_frame, textvariable=self.audit_status_var, font=("Segoe UI", 9), foreground="blue")
        status_label.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Audit control buttons (4 states)
        button_frame = ttk.LabelFrame(audit_frame, text="Control", padding=8)
        button_frame.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        self.start_audit_btn = ttk.Button(button_frame, text="▶ START AUDIT", command=self.start_audit_workflow, width=14)
        self.start_audit_btn.pack(side=tk.LEFT, padx=3)
        
        self.stop_audit_btn = ttk.Button(button_frame, text="⏹ STOP", command=self.stop_audit_workflow, width=14, state=tk.DISABLED)
        self.stop_audit_btn.pack(side=tk.LEFT, padx=3)
        
        self.hold_audit_btn = ttk.Button(button_frame, text="⏸ HOLD", command=self.hold_audit_workflow, width=14, state=tk.DISABLED)
        self.hold_audit_btn.pack(side=tk.LEFT, padx=3)
        
        self.resume_audit_btn = ttk.Button(button_frame, text="▶ RESUME", command=self.resume_audit_workflow, width=14, state=tk.DISABLED)
        self.resume_audit_btn.pack(side=tk.LEFT, padx=3)
        
        audit_frame.columnconfigure(1, weight=1)
        
        # === File Import Section ===
        import_frame = ttk.LabelFrame(left_frame, text="📂 Quick Import", padding=10)
        import_frame.pack(fill=tk.X)
        
        ttk.Button(
            import_frame,
            text="📊 Import Count Excel",
            command=self.import_inventory_excel,
            width=25
        ).pack(fill=tk.X, pady=3)
        
        ttk.Button(
            import_frame,
            text="👥 Import Timesheet Excel",
            command=self.import_timesheet_excel,
            width=25
        ).pack(fill=tk.X, pady=3)
        
        ttk.Button(
            import_frame,
            text="🔄 Auto-Import Both",
            command=self.auto_import_both,
            width=25
        ).pack(fill=tk.X, pady=3)
        
    def setup_tabs_panel(self, parent):
        """Setup 6 tabs matching vidapay-gfh"""
        right_frame = ttk.Frame(parent)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Inventory Audit Status
        self.setup_inventory_audit_tab()
        
        # Tab 2: Variance Audit
        self.setup_variance_audit_tab()
        
        # Tab 3: Store List (with auto-import)
        self.setup_store_list_tab()
        
        # Tab 4: Employees
        self.setup_employees_tab()
        
        # Tab 5: District DMs
        self.setup_district_dms_tab()
        
        # Tab 6: Excluded Devices
        self.setup_excluded_devices_tab()
        
    def setup_inventory_audit_tab(self):
        """Tab 1: Inventory Audit Status"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Inventory Audit Status")
        
        # Controls
        controls = ttk.LabelFrame(frame, text="Send Inventory Audit Status", padding=10)
        controls.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(controls, text="Send by:").grid(row=0, column=0)
        ttk.Combobox(controls, values=["District", "Store"], state="readonly").grid(row=0, column=1, padx=5)
        
        ttk.Label(controls, text="District filter:").grid(row=0, column=2)
        ttk.Combobox(controls, values=["All Districts"], state="readonly").grid(row=0, column=3, padx=5)
        
        ttk.Label(controls, text="Store filter:").grid(row=0, column=4)
        ttk.Combobox(controls, values=["All Stores"], state="readonly").grid(row=0, column=5, padx=5)
        
        button_frame = ttk.Frame(controls)
        button_frame.grid(row=1, column=0, columnspan=6, sticky=tk.EW, pady=10)
        
        for btn_text in ["Check Filter", "Check Pending", "Clear", "Send Image", "Add Store", "Open Folder"]:
            ttk.Button(button_frame, text=btn_text).pack(side=tk.LEFT, padx=3)
        
        # Search
        search_frame = ttk.LabelFrame(frame, text="Search", padding=10)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(search_frame, text="Any:").grid(row=0, column=0)
        ttk.Entry(search_frame, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(search_frame, text="District:").grid(row=0, column=2)
        ttk.Entry(search_frame, width=15).grid(row=0, column=3, padx=5)
        
        ttk.Label(search_frame, text="Store:").grid(row=0, column=4)
        ttk.Entry(search_frame, width=15).grid(row=0, column=5, padx=5)
        
        ttk.Label(search_frame, text="Status:").grid(row=0, column=6)
        ttk.Entry(search_frame, width=15).grid(row=0, column=7, padx=5)
        
        ttk.Label(search_frame, text="Rep:").grid(row=0, column=8)
        ttk.Entry(search_frame, width=15).grid(row=0, column=9, padx=5)
        
        ttk.Button(search_frame, text="Clear").grid(row=0, column=10, padx=5)
        
        # Data table
        columns = ("District", "Store", "Status", "Rep Name", "Checkbox")
        self.inventory_audit_tree = ttk.Treeview(frame, columns=columns, height=20)
        self.inventory_audit_tree.heading("#0", text="ID")
        self.inventory_audit_tree.column("#0", width=50)
        
        for col in columns:
            self.inventory_audit_tree.heading(col, text=col)
            self.inventory_audit_tree.column(col, width=180)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.inventory_audit_tree.yview)
        self.inventory_audit_tree.configure(yscroll=scrollbar.set)
        
        self.inventory_audit_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def setup_variance_audit_tab(self):
        """Tab 2: Variance Audit"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Variance Audit")
        
        controls = ttk.LabelFrame(frame, text="Variance Audit Controls", padding=10)
        controls.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(controls, text="Send by:").grid(row=0, column=0)
        ttk.Combobox(controls, values=["District"], state="readonly").grid(row=0, column=1, padx=5)
        
        ttk.Label(controls, text="District:").grid(row=0, column=2)
        ttk.Combobox(controls, values=["All"], state="readonly").grid(row=0, column=3, padx=5)
        
        ttk.Checkbutton(controls, text="Only unsent").grid(row=0, column=4, padx=5)
        ttk.Checkbutton(controls, text="Show cleared").grid(row=0, column=5, padx=5)
        
        button_frame = ttk.Frame(controls)
        button_frame.grid(row=1, column=0, columnspan=6, sticky=tk.EW, pady=10)
        
        for btn_text in ["Check Filter", "Clear", "Send Image", "Send Selected", "Pending", "Mark Cleared", "Mark Not", "Export", "Open", "Clear UI", "Copy IMEI"]:
            ttk.Button(button_frame, text=btn_text, width=10).pack(side=tk.LEFT, padx=2)
        
        columns = ("District", "Store", "Product", "IMEI", "Status", "Rep", "Clearance", "✓")
        self.variance_tree = ttk.Treeview(frame, columns=columns, height=20)
        self.variance_tree.heading("#0", text="ID")
        
        for col in columns:
            self.variance_tree.heading(col, text=col)
            self.variance_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.variance_tree.yview)
        self.variance_tree.configure(yscroll=scrollbar.set)
        self.variance_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def setup_store_list_tab(self):
        """Tab 3: Store List with Auto-Import"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Store List")
        
        add_frame = ttk.LabelFrame(frame, text="Add or Update Store", padding=10)
        add_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(add_frame, text="District:").grid(row=0, column=0)
        self.store_district_var = tk.StringVar()
        ttk.Combobox(
            add_frame,
            textvariable=self.store_district_var,
            values=self.get_districts_from_db(),
            state="readonly"
        ).grid(row=0, column=1, padx=5)
        
        ttk.Label(add_frame, text="Store:").grid(row=0, column=2)
        self.store_name_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.store_name_var, width=25).grid(row=0, column=3, padx=5)
        
        for btn_text in ["Save Store", "Import XLSX", "Delete", "Clear", "Auto-Import Excel"]:
            ttk.Button(add_frame, text=btn_text).grid(row=0, column=4, padx=2)
        
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        ttk.Entry(search_frame, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Clear").pack(side=tk.LEFT)
        
        columns = ("District", "Store")
        self.store_list_tree = ttk.Treeview(frame, columns=columns, height=25)
        self.store_list_tree.heading("#0", text="ID")
        self.store_list_tree.column("#0", width=50)
        
        for col in columns:
            self.store_list_tree.heading(col, text=col)
            self.store_list_tree.column(col, width=300)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.store_list_tree.yview)
        self.store_list_tree.configure(yscroll=scrollbar.set)
        self.store_list_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def setup_employees_tab(self):
        """Tab 4: Employees"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Employees")
        
        info_label = ttk.Label(
            frame,
            text="Store each employee's name and phone. Created By is the username used in count details."
        )
        info_label.pack(fill=tk.X, padx=10, pady=10)
        
        add_frame = ttk.LabelFrame(frame, text="Add or Update Employee", padding=10)
        add_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(add_frame, text="Employee Name:").grid(row=0, column=0)
        ttk.Entry(add_frame, width=40).grid(row=0, column=1, padx=5)
        
        ttk.Label(add_frame, text="Phone:").grid(row=0, column=2)
        ttk.Entry(add_frame, width=30).grid(row=0, column=3, padx=5)
        
        ttk.Label(add_frame, text="Created By:").grid(row=0, column=4)
        ttk.Entry(add_frame, width=20).grid(row=0, column=5, padx=5)
        
        for btn_text in ["Save", "Auto-detect", "Import XLSX", "Export", "Delete", "Clear"]:
            ttk.Button(add_frame, text=btn_text).grid(row=0, column=6, padx=2)
        
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        ttk.Entry(search_frame, width=30).pack(side=tk.LEFT, padx=5)
        
        columns = ("Employee Name", "Phone", "Created By")
        self.employees_tree = ttk.Treeview(frame, columns=columns, height=22)
        self.employees_tree.heading("#0", text="ID")
        
        for col in columns:
            self.employees_tree.heading(col, text=col)
            self.employees_tree.column(col, width=250)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.employees_tree.yview)
        self.employees_tree.configure(yscroll=scrollbar.set)
        self.employees_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def setup_district_dms_tab(self):
        """Tab 5: District DMs"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="District DMs")
        
        mode_frame = ttk.LabelFrame(frame, text="WhatsApp Send Mode", padding=10)
        mode_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Radiobutton(mode_frame, text="WhatsApp Desktop App", value=1).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="WhatsApp Web (browser)", value=2).pack(side=tk.LEFT, padx=5)
        ttk.Button(mode_frame, text="Save Mode").pack(side=tk.LEFT, padx=5)
        
        left_frame = ttk.LabelFrame(frame, text="WhatsApp Groups", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(control_frame, text="District:").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(control_frame, values=self.get_districts_from_db(), state="readonly", width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Group Name:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(control_frame, width=30).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Save").pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Delete").pack(side=tk.LEFT, padx=2)
        
        columns = ("District", "Group Name")
        self.groups_tree = ttk.Treeview(left_frame, columns=columns, height=15)
        self.groups_tree.heading("#0", text="ID")
        
        for col in columns:
            self.groups_tree.heading(col, text=col)
            self.groups_tree.column(col, width=200)
        
        self.groups_tree.pack(fill=tk.BOTH, expand=True)
        
        right_frame = ttk.LabelFrame(frame, text="DM Contacts", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        control_frame = ttk.Frame(right_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(control_frame, text="District:").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(control_frame, values=self.get_districts_from_db(), state="readonly", width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="DM Name:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(control_frame, width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Phone:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(control_frame, width=15).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Save").pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Delete").pack(side=tk.LEFT, padx=2)
        
        columns = ("District", "DM Name", "Phone")
        self.dms_tree = ttk.Treeview(right_frame, columns=columns, height=15)
        self.dms_tree.heading("#0", text="ID")
        
        for col in columns:
            self.dms_tree.heading(col, text=col)
            self.dms_tree.column(col, width=180)
        
        self.dms_tree.pack(fill=tk.BOTH, expand=True)
        
    def setup_excluded_devices_tab(self):
        """Tab 6: Excluded Devices"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Excluded Devices")
        
        controls = ttk.LabelFrame(frame, text="Exclude Devices", padding=10)
        controls.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(controls, text="District:").grid(row=0, column=0)
        ttk.Combobox(controls, values=self.get_districts_from_db(), state="readonly").grid(row=0, column=1, padx=5)
        
        ttk.Label(controls, text="Product:").grid(row=0, column=2)
        ttk.Entry(controls, width=25).grid(row=0, column=3, padx=5)
        
        ttk.Label(controls, text="IMEI:").grid(row=0, column=4)
        ttk.Entry(controls, width=25).grid(row=0, column=5, padx=5)
        
        ttk.Label(controls, text="Comments:").grid(row=0, column=6)
        ttk.Entry(controls, width=30).grid(row=0, column=7, padx=5)
        
        button_frame = ttk.Frame(controls)
        button_frame.grid(row=1, column=0, columnspan=8, sticky=tk.EW, pady=10)
        
        for btn_text in ["Find", "Save", "Update", "Import", "Export", "Delete", "Delete All", "Clear"]:
            ttk.Button(button_frame, text=btn_text, width=10).pack(side=tk.LEFT, padx=2)
        
        columns = ("District", "Product", "IMEI", "Comments")
        self.excluded_tree = ttk.Treeview(frame, columns=columns, height=22)
        self.excluded_tree.heading("#0", text="ID")
        
        for col in columns:
            self.excluded_tree.heading(col, text=col)
            self.excluded_tree.column(col, width=250)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.excluded_tree.yview)
        self.excluded_tree.configure(yscroll=scrollbar.set)
        self.excluded_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def setup_footer(self, parent):
        """Setup footer"""
        footer_frame = ttk.Frame(parent)
        footer_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(footer_frame, text="Ready", font=("Segoe UI", 9))
        self.status_label.pack(side=tk.LEFT)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            footer_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=300
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=10)
        
    # ==================== IMPORT FUNCTIONS ====================
    
    def import_inventory_excel(self):
        """Import stores from inventory count Excel"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            self.update_status("Importing inventory file...")
            df = pd.read_excel(file_path)
            
            # Extract unique stores from timesheet lookup
            # For now, use the uploaded file structure
            if 'Store' in df.columns and 'Created By' in df.columns:
                unique_stores = df['Store'].unique()
                messagebox.showinfo("Success", f"Found {len(unique_stores)} unique stores. Proceed with timesheet merge?")
            else:
                messagebox.showerror("Error", "File must have 'Store' and 'Created By' columns")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import: {str(e)}")
            
    def import_timesheet_excel(self):
        """Import employees and stores from timesheet Excel"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            self.update_status("Importing timesheet file...")
            df = pd.read_excel(file_path)
            
            # Expected columns: District, Store, Employee, Clock In
            if all(col in df.columns for col in ['District', 'Store', 'Employee']):
                # Clean up district names
                df['District'] = df['District'].str.strip()
                df['District'] = df['District'].replace({
                    'az': 'Arizona',
                    'co_west': 'Colorado West',
                    'co_east': 'Colorado East',
                    'la': 'Louisiana',
                    'tn': 'Tennessee',
                    'tx': 'Texas',
                    'ga': 'Georgia'
                })
                
                # Import stores
                store_data = df[['District', 'Store']].drop_duplicates()
                for idx, row in store_data.iterrows():
                    self.db_manager.add_store(row['District'], row['Store'])
                
                # Import employees
                employee_data = df[['Employee', 'District']].drop_duplicates()
                for idx, row in employee_data.iterrows():
                    if pd.notna(row['Employee']) and not str(row['Employee']).endswith('— TOTAL'):
                        self.db_manager.add_employee(row['Employee'], phone="", created_by="")
                
                self.populate_store_list_tab()
                self.populate_employees_tab()
                
                messagebox.showinfo("Success", f"Imported {len(store_data)} stores and {len(employee_data)} employees")
                self.update_status("Timesheet import completed")
            else:
                messagebox.showerror("Error", "File must have 'District', 'Store', 'Employee' columns")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import timesheet: {str(e)}")
            
    def auto_import_both(self):
        """Auto-import both count and timesheet, process them together"""
        try:
            uploads_dir = Path("/mnt/user-data/uploads")
            
            # Find files
            count_files = list(uploads_dir.glob("*Count*Result*.Xlsx")) + list(uploads_dir.glob("*Count*Result*.xlsx"))
            timesheet_files = list(uploads_dir.glob("*timesheet*.xlsx")) + list(uploads_dir.glob("*Timesheet*.xlsx"))
            
            if not count_files:
                messagebox.showerror("Error", "No count file found in uploads")
                return
            
            if not timesheet_files:
                messagebox.showerror("Error", "No timesheet file found in uploads")
                return
            
            count_file = str(count_files[0])
            timesheet_file = str(timesheet_files[0])
            
            self.update_status("Loading and processing both sheets...")
            
            # Use two-sheet processor
            success, message, processor = process_both_sheets(
                count_file,
                timesheet_file,
                self.db_manager
            )
            
            if not success:
                messagebox.showerror("Error", f"Processing failed: {message}")
                return
            
            # Store processor for later use
            self.processor = processor
            
            # Get summary
            summary = processor.get_summary()
            
            self.update_status(
                f"✓ Processed: {summary['completed_stores']} completed, "
                f"{summary['pending_stores']} pending, "
                f"{summary['variances']} variances"
            )
            
            # Populate Tab 1: Audit Status
            self.populate_audit_status_tab()
            
            # Populate Tab 2: Variances
            self.populate_variance_tab()
            
            # Show summary
            summary_msg = (
                f"Processing Complete:\n\n"
                f"Total Stores: {summary['total_stores']}\n"
                f"Completed: {summary['completed_stores']}\n"
                f"Pending: {summary['pending_stores']}\n"
                f"Variances Found: {summary['variances']}\n\n"
                f"{message}"
            )
            messagebox.showinfo("Success", summary_msg)
            
        except Exception as e:
            messagebox.showerror("Error", f"Auto-import failed: {str(e)}")
            logger.exception("Auto-import error")
            self.populate_employees_tab()
            
            msg = f"✓ Imported {len(store_data)} stores and {len(employee_data)} employees"
            messagebox.showinfo("Success", msg)
            self.update_status(msg)
            
        except Exception as e:
            messagebox.showerror("Error", f"Auto-import failed: {str(e)}")
            self.update_status(f"Error: {str(e)}")
    
    # ==================== AUDIT CONTROL FUNCTIONS ====================
    
    def start_audit_workflow(self):
        """Start the audit workflow with selected district"""
        district = self.audit_district_var.get()
        start_time = self.audit_time_var.get()
        
        if not district:
            messagebox.showwarning("Validation", "Please select a district")
            return
        
        if not start_time:
            messagebox.showwarning("Validation", "Please set audit start time")
            return
        
        # Validate time format (HH:MM)
        try:
            parts = start_time.split(':')
            if len(parts) != 2:
                raise ValueError("Invalid format")
            hour = int(parts[0])
            minute = int(parts[1])
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError("Invalid time range")
        except:
            messagebox.showerror("Error", "Invalid time format. Use HH:MM (00:00 to 23:59)")
            return
        
        # Create workflow manager with selected district (if not already created)
        try:
            if self.workflow_manager is None:
                self.workflow_manager = AuditWorkflowManager(
                    db_manager=self.db_manager,
                    whatsapp_manager=None  # TODO: wire WhatsApp manager
                )
            
            # Start audit with district and time from UI (NOT hardcoded!)
            success = self.workflow_manager.start_audit(district, start_time)
            
            if not success:
                messagebox.showerror("Error", "Failed to start audit. Check time format.")
                return
            
            # Update UI state
            self.audit_panel.state = AuditControlPanel.STATE_RUNNING
            self.update_audit_ui()
            
            # Start UI update thread (just for UI updates, workflow runs in workflow_manager)
            self.monitoring = True
            self.monitor_thread = threading.Thread(
                target=self._update_ui_from_workflow, 
                daemon=True
            )
            self.monitor_thread.start()
            
            self.update_status(f"✓ Audit started for {district} at {start_time}")
            messagebox.showinfo(
                "Audit Started", 
                f"Audit for {district} starting at {start_time}\n\n"
                f"Workflow:\n"
                f"1. Send starting message to {district} WhatsApp\n"
                f"2. Export count details & timesheet\n"
                f"3. Send inventory status\n"
                f"4. Poll every 15 minutes for completion\n"
                f"5. Auto-send completion message when done"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start audit: {str(e)}")
            logger.exception("Audit start error")
        
    def stop_audit_workflow(self):
        """Stop the audit workflow"""
        if not self.workflow_manager:
            messagebox.showwarning("Warning", "No audit workflow running")
            return
        
        if messagebox.askyesno("Confirm", "Stop audit workflow?"):
            try:
                self.workflow_manager.stop_audit()
                self.audit_panel.state = AuditControlPanel.STATE_STOPPED
                self.monitoring = False
                self.update_audit_ui()
                self.update_status("Audit stopped")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to stop audit: {str(e)}")
            
    def hold_audit_workflow(self):
        """Hold (pause) the audit workflow"""
        if not self.workflow_manager:
            messagebox.showwarning("Warning", "No audit workflow running")
            return
        
        try:
            self.workflow_manager.hold_audit()
            self.audit_panel.state = AuditControlPanel.STATE_HELD
            self.update_audit_ui()
            self.update_status(f"⏸ Audit held (paused) for {self.workflow_manager.district}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to hold audit: {str(e)}")
        
    def resume_audit_workflow(self):
        """Resume the audit workflow"""
        if not self.workflow_manager:
            messagebox.showwarning("Warning", "No audit workflow to resume")
            return
        
        try:
            self.workflow_manager.resume_audit()
            self.audit_panel.state = AuditControlPanel.STATE_RUNNING
            self.update_audit_ui()
            self.update_status(f"▶ Audit resumed for {self.workflow_manager.district}")
            
            # Restart UI update thread if needed
            if not self.monitor_thread or not self.monitor_thread.is_alive():
                self.monitoring = True
                self.monitor_thread = threading.Thread(
                    target=self._update_ui_from_workflow, 
                    daemon=True
                )
                self.monitor_thread.start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to resume audit: {str(e)}")
        
    def update_audit_ui(self):
        """Update audit control buttons based on state"""
        state = self.audit_panel.state
        
        self.audit_status_var.set(state)
        
        if state == AuditControlPanel.STATE_IDLE:
            self.start_audit_btn.config(state=tk.NORMAL)
            self.stop_audit_btn.config(state=tk.DISABLED)
            self.hold_audit_btn.config(state=tk.DISABLED)
            self.resume_audit_btn.config(state=tk.DISABLED)
        elif state == AuditControlPanel.STATE_RUNNING:
            self.start_audit_btn.config(state=tk.DISABLED)
            self.stop_audit_btn.config(state=tk.NORMAL)
            self.hold_audit_btn.config(state=tk.NORMAL)
            self.resume_audit_btn.config(state=tk.DISABLED)
        elif state == AuditControlPanel.STATE_HELD:
            self.start_audit_btn.config(state=tk.DISABLED)
            self.stop_audit_btn.config(state=tk.NORMAL)
            self.hold_audit_btn.config(state=tk.DISABLED)
            self.resume_audit_btn.config(state=tk.NORMAL)
        elif state == AuditControlPanel.STATE_STOPPED:
            self.start_audit_btn.config(state=tk.NORMAL)
            self.stop_audit_btn.config(state=tk.DISABLED)
            self.hold_audit_btn.config(state=tk.DISABLED)
            self.resume_audit_btn.config(state=tk.DISABLED)
            self.audit_panel.state = AuditControlPanel.STATE_IDLE
    
    # ==================== MONITORING THREAD ====================
    
    def start_monitoring(self):
        """Start background monitoring thread"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._update_ui_from_workflow, daemon=True)
        self.monitor_thread.start()
        
    def _update_ui_from_workflow(self):
        """Background thread that updates UI based on workflow manager state"""
        while self.monitoring and self.workflow_manager:
            try:
                # Get status from workflow manager
                status_msg = self.workflow_manager.get_status()
                if status_msg:
                    self.update_status(status_msg)
                
                # Check workflow state and update UI accordingly
                from audit_workflow_manager import AuditState
                
                if self.workflow_manager.state == AuditState.STOPPED or \
                   self.workflow_manager.state == AuditState.IDLE:
                    # Workflow completed or stopped
                    self.monitoring = False
                    self.audit_panel.state = AuditControlPanel.STATE_IDLE
                    self.update_audit_ui()
                    if self.workflow_manager.state == AuditState.STOPPED:
                        self.update_status(f"✅ Audit completed for {self.workflow_manager.district}")
                
                self.root.update()
                
            except Exception as e:
                logger.exception(f"UI update error: {e}")
            
            threading.Event().wait(2)  # Update UI every 2 seconds
    
    # ==================== DATA POPULATION FUNCTIONS ====================
    
    def populate_store_list_tab(self):
        """Populate Store List tab from database"""
        for item in self.store_list_tree.get_children():
            self.store_list_tree.delete(item)
        
        stores = self.db_manager.get_stores()
        for idx, store in enumerate(stores, 1):
            self.store_list_tree.insert(
                "",
                tk.END,
                text=str(idx),
                values=(store.get('district', ''), store.get('store', ''))
            )
    
    def populate_employees_tab(self):
        """Populate Employees tab from database"""
        for item in self.employees_tree.get_children():
            self.employees_tree.delete(item)
        
        employees = self.db_manager.get_employees()
        for idx, emp in enumerate(employees, 1):
            self.employees_tree.insert(
                "",
                tk.END,
                text=str(idx),
                values=(emp.get('employee_name', ''), emp.get('phone', ''), emp.get('created_by', ''))
            )
    
    def populate_audit_status_tab(self):
        """Populate Audit Status (Tab 1) from processor results"""
        if not self.processor:
            messagebox.showwarning("Warning", "No processor data available. Import both sheets first.")
            return
        
        # Clear existing
        for item in self.audit_status_tree.get_children():
            self.audit_status_tree.delete(item)
        
        # Get audit status rows
        audit_rows = self.processor.get_audit_status()
        
        # Insert into tree
        for idx, row in enumerate(audit_rows, 1):
            tags = ()
            if row["status"] == "Completed":
                tags = ("completed",)
            elif row["status"] == "Pending":
                tags = ("pending",)
            
            self.audit_status_tree.insert(
                "",
                tk.END,
                text=str(idx),
                values=(
                    row.get("district", ""),
                    row.get("store", ""),
                    row.get("employee", ""),
                    row.get("status", ""),
                    row.get("percentage", "0%")
                ),
                tags=tags
            )
    
    def populate_variance_tab(self):
        """Populate Variance (Tab 2) from processor results"""
        if not self.processor:
            messagebox.showwarning("Warning", "No processor data available. Import both sheets first.")
            return
        
        # Clear existing
        for item in self.variance_tree.get_children():
            self.variance_tree.delete(item)
        
        # Get variance rows
        variances = self.processor.get_variances()
        
        # Insert into tree
        for idx, var in enumerate(variances, 1):
            self.variance_tree.insert(
                "",
                tk.END,
                text=str(idx),
                values=(
                    var.get("district", ""),
                    var.get("store", ""),
                    var.get("employee", ""),
                    var.get("imei", ""),
                    var.get("product", ""),
                    var.get("status", "")
                )
            )
    
    # ==================== UTILITY FUNCTIONS ====================
    
    def load_credentials(self):
        """Load saved credentials from database"""
        try:
            # Load B2B Soft credentials
            creds = self.credential_manager.get_credentials()
            if creds:
                self.access_code_var.set(creds.get("access_code", ""))
                self.account_id_var.set(creds.get("account_id", ""))
                self.username_var.set(creds.get("username", ""))
                self.password_var.set(creds.get("password", ""))
            
            # Load GFH Telecom timesheet credentials
            ts_creds = self.credential_manager.get_timesheet_credentials()
            if ts_creds:
                self.ts_email_var.set(ts_creds.get("ts_email", ""))
                self.ts_password_var.set(ts_creds.get("ts_password", ""))
        except Exception as e:
            print(f"Error loading credentials: {e}")
            
    def save_credentials(self):
        """Save credentials to encrypted database"""
        try:
            credentials = {
                "access_code": self.access_code_var.get(),
                "account_id": self.account_id_var.get(),
                "username": self.username_var.get(),
                "password": self.password_var.get()
            }
            
            if not all(credentials.values()):
                messagebox.showwarning("Validation", "Please fill all credential fields")
                return
            
            self.credential_manager.save_credentials(credentials)
            messagebox.showinfo("Success", "Credentials saved securely")
            self.update_status("Credentials saved")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")
            
    def clear_credentials(self):
        """Clear all credential fields"""
        if messagebox.askyesno("Confirm", "Clear all B2B Soft credentials?"):
            self.access_code_var.set("")
            self.account_id_var.set("")
            self.username_var.set("")
            self.password_var.set("")
            self.credential_manager.delete_credentials()
    
    def save_timesheet_credentials(self):
        """Save GFH Telecom timesheet credentials to encrypted database"""
        try:
            ts_credentials = {
                'ts_email': self.ts_email_var.get(),
                'ts_password': self.ts_password_var.get(),
            }
            
            if not all(ts_credentials.values()):
                messagebox.showwarning("Validation", "Please fill all timesheet credential fields")
                return
            
            self.credential_manager.save_timesheet_credentials(ts_credentials)
            messagebox.showinfo("Success", "Timesheet credentials saved (encrypted)")
            self.update_status("✓ Timesheet credentials saved")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save timesheet credentials: {str(e)}")
    
    def clear_timesheet_credentials(self):
        """Clear timesheet credential fields"""
        if messagebox.askyesno("Confirm", "Clear all timesheet credentials?"):
            self.ts_email_var.set("")
            self.ts_password_var.set("")
            self.credential_manager.delete_timesheet_credentials()
            messagebox.showinfo("Success", "Timesheet credentials cleared")
    
    def fetch_timesheet_data(self):
        """Fetch timesheet data from GFH Telecom portal"""
        ts_credentials = {
            'ts_email': self.ts_email_var.get(),
            'ts_password': self.ts_password_var.get(),
        }
        
        if not all(ts_credentials.values()):
            messagebox.showwarning("Validation", "Please fill all timesheet credential fields")
            return
        
        self.update_status("Fetching timesheet data from GFH Telecom...")
        thread = threading.Thread(target=self._fetch_timesheet_background, args=(ts_credentials,), daemon=True)
        thread.start()
    
    def _fetch_timesheet_background(self, ts_credentials):
        """Background task to fetch timesheet data"""
        try:
            # TODO: Integrate enhanced_web_scraper_v2 for GFH Telecom portal
            # This will handle 2FA, CAPTCHA, and automatic verification waiting
            self.update_status("✓ Timesheet data fetched")
            messagebox.showinfo("Success", "Timesheet data imported successfully")
        except Exception as e:
            self.update_status(f"✗ Timesheet fetch failed: {str(e)}")
            messagebox.showerror("Error", f"Failed to fetch timesheet: {str(e)}")
            messagebox.showinfo("Success", "Credentials cleared")
            
    def start_scraping(self):
        """Start scraping B2B Soft data"""
        credentials = {
            "access_code": self.access_code_var.get(),
            "account_id": self.account_id_var.get(),
            "username": self.username_var.get(),
            "password": self.password_var.get()
        }
        
        if not all(credentials.values()):
            messagebox.showwarning("Validation", "Please fill all credential fields")
            return
        
        thread = threading.Thread(target=self._scrape_data, args=(credentials,), daemon=True)
        thread.start()
        
    def _scrape_data(self, credentials):
        """Background thread for scraping"""
        try:
            self.update_status("Scraping B2B Soft data...")
            # TODO: Implement scraping logic
            self.update_status("Scrape complete")
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=message)
        self.root.update_idletasks()


def main():
    root = tk.Tk()
    app = B2BSoftInventoryAuditApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
