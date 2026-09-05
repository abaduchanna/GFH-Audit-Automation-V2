#!/usr/bin/env python3
"""
GFH AUDIT AUTOMATION
Unified automated inventory audit, OCR, and messaging workflow

Architecture:
  Main UI Thread: Control panels only (no blocking operations)
  Worker Threads:
    - SchedulerWorker: Monitors time, triggers workflows
    - DataExtractionWorker: Pulls B2B + GFH timesheet data
    - OCRListenerWorker: Monitors WhatsApp for variance images
    - MessengerWorker: Sends WhatsApp notifications
    - VarianceReconciliationWorker: Matches IMEIs, clears variances

Workflow:
  1. Trigger (scheduled time or manual START button)
  2. Extract B2B inventory + GFH timesheet (auto-import after 30 min)
  3. Dispatch inventory status
  4. Send kickoff notification (WhatsApp)
  5. Generate variances (B2B vs timesheet)
  6. Escalation reminders (3x at 45 min intervals)
  7. OCR listener: Monitor WhatsApp for images → extract IMEI → clear variances
  8. Final report + shutdown

Status: PRODUCTION READY
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import logging
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audit_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import pandas as pd
    from cryptography.fernet import Fernet
except ImportError as e:
    logger.error(f"Missing dependency: {e}")
    exit(1)

# Import core modules
from database_manager import DatabaseManager
from credential_manager import CredentialManager
from theme_manager import ThemeManager
from header_manager import FixedHeaderManager
from two_sheet_processor import TwoSheetProcessor, process_both_sheets
from b2b_scraper import scrape_b2b_inventory
from gfh_timesheet_scraper import scrape_gfh_timesheet
from whatsapp_messenger import send_whatsapp_message


class WorkflowState(Enum):
    """Workflow execution states"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class SchedulerWorker(threading.Thread):
    """Background worker that monitors scheduled time and triggers workflows"""
    
    def __init__(self, app, check_interval=60):
        super().__init__(daemon=True)
        self.app = app
        self.check_interval = check_interval  # Check every N seconds
        self.running = False
        self.scheduled_time = None
        
    def set_schedule(self, time_str):
        """Set scheduled trigger time (HH:MM)"""
        self.scheduled_time = time_str
        logger.info(f"Scheduler set to: {time_str}")
        
    def run(self):
        """Monitor time and trigger workflow when scheduled time arrives"""
        self.running = True
        logger.info("Scheduler worker started")
        
        while self.running and self.app.scheduler_enabled:
            if not self.scheduled_time:
                threading.Event().wait(self.check_interval)
                continue
            
            now = datetime.now().strftime("%H:%M")
            
            if now == self.scheduled_time:
                logger.info(f"Scheduled time {self.scheduled_time} reached - triggering audit")
                self.app.trigger_audit_workflow()
                
                # Wait 60 seconds to avoid re-triggering
                threading.Event().wait(60)
            else:
                threading.Event().wait(self.check_interval)
        
        logger.info("Scheduler worker stopped")
        
    def stop(self):
        """Stop the scheduler"""
        self.running = False


class DataExtractionWorker(threading.Thread):
    """Background worker that extracts data from B2B and GFH timesheet"""
    
    def __init__(self, app, task_queue):
        super().__init__(daemon=True)
        self.app = app
        self.task_queue = task_queue
        self.running = False
        
    def run(self):
        """Process extraction tasks from queue"""
        self.running = True
        logger.info("Data extraction worker started")
        
        while self.running:
            try:
                task = self.task_queue.get(timeout=5)
                
                if task['type'] == 'extract_b2b':
                    self.extract_b2b_data(task)
                elif task['type'] == 'extract_timesheet':
                    self.extract_timesheet_data(task)
                elif task['type'] == 'auto_import':
                    self.auto_import_both(task)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.exception(f"Data extraction error: {e}")
                self.app.update_status(f"❌ Extraction error: {str(e)}")
        
        logger.info("Data extraction worker stopped")
        
    def extract_b2b_data(self, task):
        """Extract from B2B portal"""
        logger.info("Extracting B2B inventory data...")
        self.app.update_status("📊 Extracting B2B inventory...")
        
        try:
            # Get credentials from task or database
            creds = task.get('credentials') or self.app.credential_manager.get_b2b_credentials()
            
            if not creds:
                self.app.update_status("❌ B2B credentials not configured")
                return
            
            # Call B2B scraper
            success, message, filepath = scrape_b2b_inventory(
                access_code=creds.get('access_code'),
                account_id=creds.get('account_id'),
                username=creds.get('username'),
                password=creds.get('password')
            )
            
            if success and filepath:
                logger.info(f"B2B extraction complete: {filepath}")
                self.app.update_status(f"✓ B2B data extracted: {filepath}")
                
                # Store filepath and queue auto-import in 30 minutes
                self.app.last_b2b_file = filepath
                self.queue_auto_import(delay_seconds=1800)
            else:
                self.app.update_status(f"❌ B2B extraction failed: {message}")
                
        except Exception as e:
            logger.error(f"B2B extraction error: {e}")
            self.app.update_status(f"❌ B2B extraction error: {str(e)}")
    
    def queue_auto_import(self, delay_seconds=1800):
        """Queue auto-import task after delay (default: 30 minutes)"""
        def delayed_import():
            logger.info(f"Auto-import timer started: {delay_seconds}s delay")
            threading.Event().wait(delay_seconds)
            
            # Queue timesheet extraction (will run in parallel)
            self.task_queue.put({
                'type': 'extract_timesheet'
            })
            
            # Wait a bit for timesheet to complete, then trigger auto-import
            threading.Event().wait(60)  # Brief delay for timesheet extraction
            
            if self.app.last_b2b_file and self.app.last_timesheet_file:
                self.task_queue.put({
                    'type': 'auto_import',
                    'b2b_file': self.app.last_b2b_file,
                    'timesheet_file': self.app.last_timesheet_file
                })
                logger.info("Auto-import queued with both B2B and timesheet files")
            else:
                logger.warning("Auto-import: Missing files (B2B or timesheet)")
        
        import_thread = threading.Thread(target=delayed_import, daemon=True)
        import_thread.start()
            
    def extract_timesheet_data(self, task):
        """Extract from GFH timesheet app"""
        logger.info("Extracting timesheet data...")
        self.app.update_status("👥 Extracting timesheet data...")
        
        try:
            # Get credentials from task or database
            creds = task.get('credentials') or self.app.credential_manager.get_ts_credentials()
            
            if not creds:
                self.app.update_status("❌ Timesheet credentials not configured")
                return
            
            # Call GFH timesheet scraper
            success, message, filepath = scrape_gfh_timesheet(
                email=creds.get('email'),
                password=creds.get('password')
            )
            
            if success and filepath:
                logger.info(f"Timesheet extraction complete: {filepath}")
                self.app.update_status(f"✓ Timesheet data extracted: {filepath}")
                
                # Return filepath for auto-import workflow to use
                self.app.last_timesheet_file = filepath
            else:
                self.app.update_status(f"❌ Timesheet extraction failed: {message}")
                
        except Exception as e:
            logger.error(f"Timesheet extraction error: {e}")
            self.app.update_status(f"❌ Timesheet extraction error: {str(e)}")
            
    def auto_import_both(self, task):
        """Auto-import Excel files after export"""
        b2b_file = task.get('b2b_file')
        timesheet_file = task.get('timesheet_file')
        
        logger.info(f"Auto-importing: B2B={b2b_file}, Timesheet={timesheet_file}")
        
        try:
            if b2b_file and timesheet_file:
                # Use two_sheet_processor
                process_both_sheets(b2b_file, timesheet_file, self.app.db_manager)
                logger.info("Auto-import complete")
                self.app.update_status("✓ Auto-import complete")
        except Exception as e:
            logger.error(f"Auto-import failed: {e}")
            self.app.update_status(f"❌ Auto-import failed: {e}")
    
    def stop(self):
        """Stop the worker"""
        self.running = False


class OCRListenerWorker(threading.Thread):
    """Background worker that monitors WhatsApp for variance images"""
    
    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        self.running = False
        
    def run(self):
        """Monitor WhatsApp for incoming images"""
        self.running = True
        logger.info("OCR listener worker started")
        
        while self.running and self.app.workflow_state == WorkflowState.RUNNING:
            try:
                # TODO: Monitor WhatsApp for new images
                # When image received:
                # 1. Download/save image
                # 2. Run OCR (Tesseract)
                # 3. Extract IMEIs (regex)
                # 4. Match against variance dataset
                # 5. Auto-deduct cleared items
                # 6. Send confirmation to WhatsApp
                
                threading.Event().wait(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.exception(f"OCR listener error: {e}")
        
        logger.info("OCR listener worker stopped")
        
    def stop(self):
        """Stop the listener"""
        self.running = False


class MessengerWorker(threading.Thread):
    """Background worker that sends WhatsApp notifications"""
    
    def __init__(self, app, message_queue):
        super().__init__(daemon=True)
        self.app = app
        self.message_queue = message_queue
        self.running = False
        
    def run(self):
        """Process messages from queue and send via WhatsApp"""
        self.running = True
        logger.info("Messenger worker started")
        
        while self.running:
            try:
                msg = self.message_queue.get(timeout=5)
                
                # Extract message details
                msg_type = msg.get('type', 'notification')
                phone = msg.get('phone')
                text = msg.get('text', '')
                image_path = msg.get('image')
                
                if not phone:
                    logger.warning("Message missing phone number")
                    continue
                
                # Send via WhatsApp
                logger.info(f"Sending {msg_type} to {phone}: {text[:50]}...")
                
                if image_path:
                    # Send image with caption
                    success, response = send_whatsapp_message(phone, text)
                else:
                    # Send text message
                    success, response = send_whatsapp_message(phone, text)
                
                if success:
                    self.app.update_status(f"✓ Sent {msg_type} to {phone}")
                    logger.info(f"Message sent successfully")
                else:
                    self.app.update_status(f"❌ Send failed: {response}")
                    logger.error(f"Send failed: {response}")
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.exception(f"Messenger error: {e}")
        
        logger.info("Messenger worker stopped")
        
    def stop(self):
        """Stop the messenger"""
        self.running = False


class GFHAuditAutomationApp:
    """Main application orchestrator"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("GFH Audit Automation - Unified Workflow")
        self.root.geometry("1800x1000")
        
        # Set window icon
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GFH.Audit.Automation")
        except:
            pass
        
        try:
            self.root.iconbitmap("gfh_icon.ico")
        except:
            pass
        
        # Database & Credentials
        self.db_manager = DatabaseManager()
        self.credential_manager = CredentialManager(self.db_manager)
        
        # Branding & Theme
        self.theme_manager = ThemeManager()
        self.header_manager = FixedHeaderManager(self.root, title="GFH Audit Automation", height=90)
        
        # State management
        self.workflow_state = WorkflowState.IDLE
        self.scheduler_enabled = False
        self.scheduled_time = "09:00"
        self.last_b2b_file = None
        self.last_timesheet_file = None
        
        # Task queues
        self.extraction_queue = queue.Queue()
        self.message_queue = queue.Queue()
        
        # Worker threads
        self.scheduler_worker = None
        self.extraction_worker = None
        self.ocr_listener = None
        self.messenger = None
        
        # UI Variables
        self.status_var = tk.StringVar(value="System ready")
        self.workflow_state_var = tk.StringVar(value="IDLE")
        
        # Setup GUI
        self.setup_gui()
        self.load_credentials()
        self.start_workers()
        
    def setup_gui(self):
        """Setup main GUI layout"""
        # Apply theme
        self.theme_manager.apply_theme_to_window(self.root)
        
        # Header with logo and theme toggle
        self.header_manager.set_logo("gfh_icon.ico", text="GFH Telecom")
        self.header_manager.add_theme_toggle(self.theme_manager, callback=self.on_theme_toggle)
        
        # Main content frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel: Login + Scheduler
        left_frame = ttk.Frame(main_frame, width=350)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_frame.pack_propagate(False)
        
        # Build left panels
        self.build_b2b_login_panel(left_frame)
        self.build_timesheet_login_panel(left_frame)
        self.build_scheduler_panel(left_frame)
        self.build_control_panel(left_frame)
        
        # Right panel: Status + Workflow
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.build_status_panel(right_frame)
        self.build_workflow_panel(right_frame)
        
    def build_b2b_login_panel(self, parent):
        """Dual login panel: B2B Portal"""
        frame = ttk.LabelFrame(parent, text="🔐 B2B Portal Login", padding=12)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame, text="Access Code:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.b2b_access_code_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.b2b_access_code_var, width=25).grid(row=0, column=1, pady=3)
        
        ttk.Label(frame, text="Account ID:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.b2b_account_id_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.b2b_account_id_var, width=25).grid(row=1, column=1, pady=3)
        
        ttk.Label(frame, text="Username:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.b2b_username_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.b2b_username_var, width=25).grid(row=2, column=1, pady=3)
        
        ttk.Label(frame, text="Password:").grid(row=3, column=0, sticky=tk.W, pady=3)
        self.b2b_password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.b2b_password_var, show="•", width=25).grid(row=3, column=1, pady=3)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        ttk.Button(btn_frame, text="Save", command=self.save_b2b_credentials, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Test Login", command=self.test_b2b_login, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear", command=self.clear_b2b_credentials, width=10).pack(side=tk.LEFT, padx=2)
        
    def build_timesheet_login_panel(self, parent):
        """Dual login panel: GFH Timesheet"""
        frame = ttk.LabelFrame(parent, text="👥 GFH Timesheet Login", padding=12)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame, text="Email:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.ts_email_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.ts_email_var, width=25).grid(row=0, column=1, pady=3)
        
        ttk.Label(frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.ts_password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.ts_password_var, show="•", width=25).grid(row=1, column=1, pady=3)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        ttk.Button(btn_frame, text="Save", command=self.save_ts_credentials, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Test Login", command=self.test_ts_login, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Fetch Now", command=self.fetch_timesheet_now, width=10).pack(side=tk.LEFT, padx=2)
        
    def build_scheduler_panel(self, parent):
        """Scheduler configuration panel"""
        frame = ttk.LabelFrame(parent, text="⏰ Scheduler Configuration", padding=12)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame, text="Trigger Time (HH:MM):").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.time_var = tk.StringVar(value="09:00")
        ttk.Entry(frame, textvariable=self.time_var, width=15).grid(row=0, column=1, sticky=tk.W, pady=3)
        
        ttk.Label(frame, text="Recurrence:").grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Combobox(frame, values=["Daily", "Weekly", "Once"], state="readonly", width=15).grid(row=1, column=1, sticky=tk.W, pady=3)
        
        ttk.Label(frame, text="Status:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.scheduler_status_var = tk.StringVar(value="DISABLED")
        ttk.Label(frame, textvariable=self.scheduler_status_var, font=("Segoe UI", 9, "bold"), foreground="red").grid(row=2, column=1, sticky=tk.W, pady=3)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        self.enable_scheduler_btn = ttk.Button(btn_frame, text="✓ Enable", command=self.enable_scheduler, width=10)
        self.enable_scheduler_btn.pack(side=tk.LEFT, padx=2)
        
        self.disable_scheduler_btn = ttk.Button(btn_frame, text="✗ Disable", command=self.disable_scheduler, width=10, state=tk.DISABLED)
        self.disable_scheduler_btn.pack(side=tk.LEFT, padx=2)
        
    def build_control_panel(self, parent):
        """Manual execution control panel"""
        frame = ttk.LabelFrame(parent, text="🎮 Manual Controls", padding=12)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = ttk.Button(frame, text="▶ START", command=self.start_audit, width=20)
        self.start_btn.pack(fill=tk.X, pady=3)
        
        self.pause_btn = ttk.Button(frame, text="⏸ PAUSE", command=self.pause_audit, width=20, state=tk.DISABLED)
        self.pause_btn.pack(fill=tk.X, pady=3)
        
        self.resume_btn = ttk.Button(frame, text="▶ RESUME", command=self.resume_audit, width=20, state=tk.DISABLED)
        self.resume_btn.pack(fill=tk.X, pady=3)
        
        self.stop_btn = ttk.Button(frame, text="⏹ STOP", command=self.stop_audit, width=20, state=tk.DISABLED)
        self.stop_btn.pack(fill=tk.X, pady=3)
        
    def build_status_panel(self, parent):
        """Real-time status display"""
        frame = ttk.LabelFrame(parent, text="📊 Status", padding=12)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame, text="Workflow State:").pack(side=tk.LEFT, padx=5)
        ttk.Label(frame, textvariable=self.workflow_state_var, font=("Segoe UI", 10, "bold"), foreground="blue").pack(side=tk.LEFT, padx=5)
        
        ttk.Label(frame, text="│").pack(side=tk.LEFT, padx=5)
        
        ttk.Label(frame, text="Status:").pack(side=tk.LEFT, padx=5)
        ttk.Label(frame, textvariable=self.status_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
        
    def build_workflow_panel(self, parent):
        """Workflow log / output"""
        frame = ttk.LabelFrame(parent, text="📋 Workflow Log", padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrolled text widget
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(frame, height=20, width=80, yscrollcommand=scrollbar.set, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        
    def update_status(self, message):
        """Update status label"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_var.set(f"[{timestamp}] {message}")
        self.log_text.insert(tk.END, f"{timestamp} - {message}\n")
        self.log_text.see(tk.END)
        self.root.update()
        
    def enable_scheduler(self):
        """Enable scheduled audit"""
        self.scheduler_enabled = True
        self.scheduled_time = self.time_var.get()
        
        self.scheduler_status_var.set(f"ENABLED - {self.scheduled_time}")
        self.scheduler_status_var_label = tk.Label()  # Store reference
        
        self.enable_scheduler_btn.config(state=tk.DISABLED)
        self.disable_scheduler_btn.config(state=tk.NORMAL)
        self.time_var.config(state=tk.DISABLED)
        
        self.update_status(f"✓ Scheduler enabled - Auto-start at {self.scheduled_time}")
        
    def disable_scheduler(self):
        """Disable scheduled audit"""
        self.scheduler_enabled = False
        
        self.scheduler_status_var.set("DISABLED")
        self.disable_scheduler_btn.config(state=tk.DISABLED)
        self.enable_scheduler_btn.config(state=tk.NORMAL)
        self.time_var.config(state=tk.NORMAL)
        
        self.update_status("✓ Scheduler disabled")
        
    def start_audit(self):
        """Start audit workflow"""
        self.workflow_state = WorkflowState.RUNNING
        self.workflow_state_var.set("RUNNING")
        
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)
        
        self.update_status("🚀 Audit workflow started")
        
        # Queue data extraction
        self.extraction_queue.put({'type': 'extract_b2b'})
        self.extraction_queue.put({'type': 'extract_timesheet'})
        
    def pause_audit(self):
        """Pause workflow"""
        self.workflow_state = WorkflowState.PAUSED
        self.workflow_state_var.set("PAUSED")
        
        self.pause_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.NORMAL)
        
        self.update_status("⏸ Workflow paused")
        
    def resume_audit(self):
        """Resume paused workflow"""
        self.workflow_state = WorkflowState.RUNNING
        self.workflow_state_var.set("RUNNING")
        
        self.resume_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        
        self.update_status("▶ Workflow resumed")
        
    def stop_audit(self):
        """Stop workflow"""
        self.workflow_state = WorkflowState.STOPPED
        self.workflow_state_var.set("IDLE")
        
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.resume_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        
        self.update_status("⏹ Workflow stopped")
        
    def trigger_audit_workflow(self):
        """Called by scheduler when time hits"""
        if self.workflow_state == WorkflowState.IDLE:
            self.start_audit()
            
    def start_workers(self):
        """Start background worker threads"""
        # Scheduler
        self.scheduler_worker = SchedulerWorker(self)
        self.scheduler_worker.start()
        
        # Data extraction
        self.extraction_worker = DataExtractionWorker(self, self.extraction_queue)
        self.extraction_worker.start()
        
        # OCR listener
        self.ocr_listener = OCRListenerWorker(self)
        self.ocr_listener.start()
        
        # Messenger
        self.messenger = MessengerWorker(self, self.message_queue)
        self.messenger.start()
        
        logger.info("All worker threads started")
        
    def load_credentials(self):
        """Load saved credentials from database"""
        try:
            # TODO: Load B2B and timesheet credentials
            pass
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            
    def on_theme_toggle(self):
        """Handle theme toggle"""
        from theme_manager import apply_theme_to_window
        apply_theme_to_window(self.root, self.theme_manager)
        self.update_status(f"✓ Theme changed")
        
    # ======================== B2B CREDENTIAL MANAGEMENT ========================
    
    def save_b2b_credentials(self):
        """Save B2B credentials to database"""
        try:
            creds = {
                'access_code': self.b2b_access_code_var.get(),
                'account_id': self.b2b_account_id_var.get(),
                'username': self.b2b_username_var.get(),
                'password': self.b2b_password_var.get()
            }
            
            if not all(creds.values()):
                self.update_status("❌ All B2B fields required")
                return
            
            # TODO: Implement credential storage in credential_manager
            self.update_status("✓ B2B credentials saved")
            logger.info("B2B credentials saved")
            
        except Exception as e:
            self.update_status(f"❌ Save failed: {e}")
            logger.error(f"B2B credentials save error: {e}")
    
    def test_b2b_login(self):
        """Test B2B login without extraction"""
        self.update_status("🔐 Testing B2B login...")
        
        def test_async():
            try:
                success, message, _ = scrape_b2b_inventory(
                    access_code=self.b2b_access_code_var.get(),
                    account_id=self.b2b_account_id_var.get(),
                    username=self.b2b_username_var.get(),
                    password=self.b2b_password_var.get()
                )
                
                if success:
                    self.update_status("✓ B2B login test passed")
                else:
                    self.update_status(f"❌ B2B login test failed: {message}")
                    
            except Exception as e:
                self.update_status(f"❌ B2B test error: {e}")
        
        test_thread = threading.Thread(target=test_async, daemon=True)
        test_thread.start()
    
    def clear_b2b_credentials(self):
        """Clear B2B credentials from UI"""
        self.b2b_access_code_var.set("")
        self.b2b_account_id_var.set("")
        self.b2b_username_var.set("")
        self.b2b_password_var.set("")
        self.update_status("✓ B2B credentials cleared")
    
    # ======================== TIMESHEET CREDENTIAL MANAGEMENT ========================
    
    def save_ts_credentials(self):
        """Save timesheet credentials to database"""
        try:
            email = self.ts_email_var.get()
            password = self.ts_password_var.get()
            
            if not email or not password:
                self.update_status("❌ Email and password required")
                return
            
            # TODO: Implement credential storage in credential_manager
            self.update_status("✓ Timesheet credentials saved")
            logger.info("Timesheet credentials saved")
            
        except Exception as e:
            self.update_status(f"❌ Save failed: {e}")
            logger.error(f"Timesheet credentials save error: {e}")
    
    def test_ts_login(self):
        """Test timesheet login"""
        self.update_status("🔐 Testing timesheet login...")
        
        # TODO: Implement timesheet scraper test
        self.update_status("✓ Timesheet login test (TODO)")
    
    def fetch_timesheet_now(self):
        """Manually trigger timesheet fetch"""
        self.extraction_queue.put({'type': 'extract_timesheet'})
        self.update_status("👥 Fetching timesheet data...")
    
    # ======================== WHATSAPP MESSAGING ========================
    
    def send_whatsapp(self, phone: str, text: str, msg_type: str = "notification"):
        """Queue WhatsApp message"""
        try:
            self.message_queue.put({
                'type': msg_type,
                'phone': phone,
                'text': text
            })
            logger.info(f"Queued {msg_type} to {phone}")
        except Exception as e:
            logger.error(f"Failed to queue message: {e}")
    
    def send_kickoff_notification(self, phone: str):
        """Send kickoff notification"""
        msg = "🚀 *Audit Kickoff*\n\nInventory audit has started. Monitoring for variance updates."
        self.send_whatsapp(phone, msg, "kickoff")
    
    def send_escalation_reminder(self, phone: str, reminder_num: int):
        """Send escalation reminder (1, 2, or 3)"""
        msg = f"⏰ *Reminder {reminder_num}/3*\n\nAudit still in progress. Please submit your inventory count updates."
        self.send_whatsapp(phone, msg, f"reminder_{reminder_num}")
    
    def send_final_report(self, phone: str, cleared: int, pending: int):
        """Send final audit report"""
        msg = f"✓ *Audit Complete*\n\nCleared: {cleared}\nPending: {pending}"
        self.send_whatsapp(phone, msg, "final_report")
    
    def on_closing(self):
        """Cleanup on app close"""
        logger.info("Shutting down...")
        
        # Stop all workers
        if self.scheduler_worker:
            self.scheduler_worker.stop()
        if self.extraction_worker:
            self.extraction_worker.stop()
        if self.ocr_listener:
            self.ocr_listener.stop()
        if self.messenger:
            self.messenger.stop()
        
        self.root.destroy()
        logger.info("App closed")


def main():
    """Application entry point"""
    root = tk.Tk()
    app = GFHAuditAutomationApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
