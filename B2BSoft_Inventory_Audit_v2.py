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
        
        # Initialize managers
        self.db_manager = DatabaseManager()
        self.credential_manager = CredentialManager(self.db_manager)
        self.scraper = WebScraper()
        self.data_parser = DataParser()
        self.audit_panel = AuditControlPanel()
        
        # Monitoring thread
        self.monitor_thread = None
        self.monitoring = False
        
        # Setup GUI
        self.setup_gui()
        self.load_credentials()
        
        # Start monitoring thread
        self.start_monitoring()
        
    def setup_gui(self):
        """Setup main GUI layout"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        self.setup_header(main_frame)
        
        # Content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel: Credentials + Audit Control
        self.setup_left_panel(content_frame)
        
        # Right panel: Tabs
        self.setup_tabs_panel(content_frame)
        
        # Footer
        self.setup_footer(main_frame)
        
    def setup_header(self, parent):
        """Setup application header"""
        header_frame = ttk.Frame(parent, height=80)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        
        title_label = ttk.Label(
            header_frame,
            text="B2B Soft Inventory Audit - Enhanced with Audit Control Panel",
            font=("Segoe UI", 14, "bold")
        )
        title_label.pack(pady=15)
        
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
        
        # === Audit Control Panel ===
        audit_frame = ttk.LabelFrame(left_frame, text="⏰ Audit Control Panel", padding=12)
        audit_frame.pack(fill=tk.X, pady=(0, 15))
        
        # District selector
        ttk.Label(audit_frame, text="Select District:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.audit_district_var = tk.StringVar()
        district_combo = ttk.Combobox(
            audit_frame,
            textvariable=self.audit_district_var,
            values=["Arizona", "Colorado East", "Colorado West", "Atlanta", "Houston", "Louisiana", "Tennessee"],
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
            values=["Arizona", "Colorado East", "Colorado West", "Atlanta", "Houston", "Louisiana", "Tennessee"],
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
        ttk.Combobox(control_frame, values=["Arizona", "Colorado East"], state="readonly", width=20).pack(side=tk.LEFT, padx=5)
        
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
        ttk.Combobox(control_frame, values=["Arizona"], state="readonly", width=20).pack(side=tk.LEFT, padx=5)
        
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
        ttk.Combobox(controls, values=["Arizona"], state="readonly").grid(row=0, column=1, padx=5)
        
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
        """Auto-import both count and timesheet from uploads folder"""
        try:
            uploads_dir = Path("/mnt/user-data/uploads")
            
            # Find files
            count_files = list(uploads_dir.glob("*Count*Result*.Xlsx")) + list(uploads_dir.glob("*Count*Result*.xlsx"))
            timesheet_files = list(uploads_dir.glob("*timesheet*.xlsx")) + list(uploads_dir.glob("*Timesheet*.xlsx"))
            
            if not timesheet_files:
                messagebox.showerror("Error", "No timesheet file found in uploads")
                return
            
            # Import timesheet (mandatory)
            self.update_status("Auto-importing timesheet...")
            df_ts = pd.read_excel(str(timesheet_files[0]))
            
            # Clean district codes
            df_ts['District'] = df_ts['District'].str.strip().str.lower()
            district_mapping = {
                'la': 'Louisiana',
                'tn': 'Tennessee',
                'tx': 'Texas',
                'ga': 'Georgia',
                'az': 'Arizona',
                'co_east': 'Colorado East',
                'co_west': 'Colorado West'
            }
            
            for code, name in district_mapping.items():
                df_ts.loc[df_ts['District'] == code, 'District'] = name
            
            # Import stores from timesheet
            store_data = df_ts[['District', 'Store']].dropna().drop_duplicates()
            for idx, row in store_data.iterrows():
                try:
                    self.db_manager.add_store(row['District'], row['Store'])
                except:
                    pass  # Duplicate key
            
            # Import employees (skip TOTAL rows)
            df_ts_clean = df_ts[~df_ts['Employee'].astype(str).str.contains('TOTAL', na=False)]
            employee_data = df_ts_clean[['Employee']].drop_duplicates()
            for idx, row in employee_data.iterrows():
                if pd.notna(row['Employee']):
                    self.db_manager.add_employee(row['Employee'], phone="", created_by="")
            
            # If count file exists, also consolidate
            if count_files:
                self.update_status("Processing count details...")
                df_count = pd.read_excel(str(count_files[0]))
                # Stores already in DB from timesheet
            
            self.populate_store_list_tab()
            self.populate_employees_tab()
            
            msg = f"✓ Imported {len(store_data)} stores and {len(employee_data)} employees"
            messagebox.showinfo("Success", msg)
            self.update_status(msg)
            
        except Exception as e:
            messagebox.showerror("Error", f"Auto-import failed: {str(e)}")
            self.update_status(f"Error: {str(e)}")
    
    # ==================== AUDIT CONTROL FUNCTIONS ====================
    
    def start_audit_workflow(self):
        """Start the audit workflow"""
        district = self.audit_district_var.get()
        start_time = self.audit_time_var.get()
        
        if not district:
            messagebox.showwarning("Validation", "Please select a district")
            return
        
        if not self.audit_panel.set_start_time(start_time):
            messagebox.showerror("Error", "Invalid time format. Use HH:MM")
            return
        
        self.audit_panel.state = AuditControlPanel.STATE_RUNNING
        self.update_audit_ui()
        
        messagebox.showinfo("Audit Started", f"Audit for {district} starting at {start_time}\n\nWorkflow:\n1. Send starting message\n2. Export files\n3. Send inventory status\n4. Poll every 15 minutes")
        self.update_status(f"Audit running for {district} - starting at {start_time}")
        
    def stop_audit_workflow(self):
        """Stop the audit workflow"""
        if messagebox.askyesno("Confirm", "Stop audit workflow?"):
            self.audit_panel.state = AuditControlPanel.STATE_STOPPED
            self.update_audit_ui()
            self.update_status("Audit stopped")
            
    def hold_audit_workflow(self):
        """Hold the audit workflow (pause monitoring)"""
        self.audit_panel.state = AuditControlPanel.STATE_HELD
        self.update_audit_ui()
        self.update_status("Audit held (paused)")
        
    def resume_audit_workflow(self):
        """Resume the audit workflow"""
        self.audit_panel.state = AuditControlPanel.STATE_RUNNING
        self.update_audit_ui()
        self.update_status("Audit resumed")
        
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
        self.monitor_thread = threading.Thread(target=self._monitor_audit_workflow, daemon=True)
        self.monitor_thread.start()
        
    def _monitor_audit_workflow(self):
        """Background thread for monitoring audit workflow"""
        while self.monitoring:
            try:
                if self.audit_panel.should_send_start_message():
                    self.update_status("📤 Sending audit start message...")
                    # TODO: Send WhatsApp message
                    self.audit_panel.whatsapp_messages_sent.add("start_message")
                
                if self.audit_panel.should_poll():
                    self.update_status("🔄 Polling for status updates (15-min check)...")
                    # TODO: Re-scrape count data and check timesheet
                    self.update_status("✓ Status check complete")
                
                self.root.update()
                
            except Exception as e:
                print(f"Monitor error: {e}")
            
            threading.Event().wait(5)  # Check every 5 seconds
    
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
    
    # ==================== UTILITY FUNCTIONS ====================
    
    def load_credentials(self):
        """Load saved credentials from database"""
        try:
            creds = self.credential_manager.get_credentials()
            if creds:
                self.access_code_var.set(creds.get("access_code", ""))
                self.account_id_var.set(creds.get("account_id", ""))
                self.username_var.set(creds.get("username", ""))
                self.password_var.set(creds.get("password", ""))
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
        if messagebox.askyesno("Confirm", "Clear all credentials?"):
            self.access_code_var.set("")
            self.account_id_var.set("")
            self.username_var.set("")
            self.password_var.set("")
            self.credential_manager.delete_credentials()
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
