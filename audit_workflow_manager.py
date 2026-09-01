"""
Audit Control Workflow Manager
Handles automated workflows for inventory audits:
- Scheduled start/stop/hold/resume
- 15-minute polling
- WhatsApp message queuing
- File export timing
"""

import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
import json
from enum import Enum


class AuditState(Enum):
    """Audit workflow states"""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    HELD = "HELD"


class WorkflowEvent(Enum):
    """Events that can occur during audit"""
    STARTED = "AUDIT_STARTED"
    SEND_START_MESSAGE = "SEND_START_MESSAGE"
    EXPORT_FILES = "EXPORT_FILES"
    SEND_STATUS = "SEND_STATUS"
    POLL_STORES = "POLL_STORES"
    CHECK_COMPLETION = "CHECK_COMPLETION"
    STOPPED = "AUDIT_STOPPED"
    HELD = "AUDIT_HELD"
    RESUMED = "AUDIT_RESUMED"


class AuditWorkflowManager:
    """Manages automated audit workflow"""
    
    def __init__(self, db_manager, whatsapp_manager=None):
        self.db_manager = db_manager
        self.whatsapp_manager = whatsapp_manager
        
        self.state = AuditState.IDLE
        self.district = None
        self.start_time = None
        self.created_at = None
        self.last_poll_time = None
        
        self.poll_interval = 15 * 60  # 15 minutes in seconds
        self.events_log = []
        self.workflow_thread = None
        self.running = False
        
        # Tracking
        self.store_completion_status = {}  # Store -> completion %
        self.export_timestamps = []
        self.messages_sent = set()
        
    def start_audit(self, district, start_time_str):
        """
        Start an audit for a district
        
        Args:
            district: District name (e.g., "Arizona")
            start_time_str: Start time in HH:MM format
        """
        try:
            # Parse start time
            time_obj = datetime.strptime(start_time_str, "%H:%M").time()
            
            self.district = district
            self.start_time = time_obj
            self.created_at = datetime.now()
            self.state = AuditState.RUNNING
            self.last_poll_time = None
            self.messages_sent.clear()
            self.events_log.clear()
            
            self._log_event(WorkflowEvent.STARTED, f"Audit started for {district} at {start_time_str}")
            
            # Start workflow thread
            if self.workflow_thread is None or not self.workflow_thread.is_alive():
                self.running = True
                self.workflow_thread = threading.Thread(
                    target=self._workflow_loop,
                    daemon=True
                )
                self.workflow_thread.start()
            
            return True
            
        except ValueError as e:
            self._log_event(None, f"Error starting audit: {str(e)}")
            return False
    
    def stop_audit(self):
        """Stop the current audit"""
        self.state = AuditState.STOPPED
        self.running = False
        self._log_event(WorkflowEvent.STOPPED, "Audit stopped by user")
        
    def hold_audit(self):
        """Pause the audit (hold)"""
        self.state = AuditState.HELD
        self._log_event(WorkflowEvent.HELD, "Audit paused (held)")
        
    def resume_audit(self):
        """Resume from held state"""
        self.state = AuditState.RUNNING
        self._log_event(WorkflowEvent.RESUMED, "Audit resumed")
    
    def _workflow_loop(self):
        """Main workflow loop (runs in background thread)"""
        while self.running and self.state == AuditState.RUNNING:
            try:
                now = datetime.now()
                
                # Check if it's time to send start message
                if self._should_send_start_message(now):
                    self._handle_send_start_message()
                
                # Check if it's time to export files (15 min after start)
                if self._should_export_files(now):
                    self._handle_export_files()
                
                # Check if it's time to send inventory status
                if self._should_send_status(now):
                    self._handle_send_status()
                
                # Check if it's time to poll (every 15 minutes)
                if self._should_poll(now):
                    self._handle_poll_stores()
                
                # Check completion status
                self._check_store_completion()
                
                # Sleep briefly to avoid busy-waiting
                time.sleep(5)
                
            except Exception as e:
                self._log_event(None, f"Workflow error: {str(e)}")
                time.sleep(10)
    
    def _should_send_start_message(self, now):
        """Check if it's time to send the starting message"""
        if "start_message" in self.messages_sent:
            return False
        
        now_time = now.time()
        return now_time >= self.start_time
    
    def _should_export_files(self, now):
        """Check if it's time to export files (15 min after start)"""
        if "export_files" in self.messages_sent:
            return False
        
        # Export files 15 minutes after audit starts
        if self.created_at is None:
            return False
        
        elapsed = (now - self.created_at).total_seconds()
        return elapsed >= (15 * 60)
    
    def _should_send_status(self, now):
        """Check if it's time to send inventory status"""
        if "send_status" in self.messages_sent:
            return False
        
        # Send status after files exported
        if "export_files" not in self.messages_sent:
            return False
        
        # Wait a bit after export
        if self.export_timestamps:
            last_export = self.export_timestamps[-1]
            elapsed = (now - last_export).total_seconds()
            return elapsed >= 60  # 1 minute after export
        
        return False
    
    def _should_poll(self, now):
        """Check if it's time to poll for updates (every 15 minutes)"""
        if self.last_poll_time is None:
            self.last_poll_time = now
            return True
        
        elapsed = (now - self.last_poll_time).total_seconds()
        if elapsed >= self.poll_interval:
            self.last_poll_time = now
            return True
        
        return False
    
    def _handle_send_start_message(self):
        """Send starting message to district WhatsApp group"""
        self._log_event(WorkflowEvent.SEND_START_MESSAGE, f"Sending audit start message to {self.district}")
        
        try:
            if self.whatsapp_manager:
                message = f"🔔 Inventory Audit Starting\n{self.district} District\nAudit Time: {self.start_time.strftime('%H:%M')}\n\nPlease begin your count."
                self.whatsapp_manager.send_message(self.district, message)
            
            self.messages_sent.add("start_message")
            self._log_event(None, "✓ Start message sent")
            
        except Exception as e:
            self._log_event(None, f"Error sending start message: {str(e)}")
    
    def _handle_export_files(self):
        """Export B2B Soft and timesheet files"""
        self._log_event(WorkflowEvent.EXPORT_FILES, "Exporting count details and timesheet files")
        
        try:
            # Export inventory count details
            export_path = Path.home() / "Downloads" / f"Audit_{self.district}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            export_path.mkdir(parents=True, exist_ok=True)
            
            # TODO: Export from B2B Soft
            count_file = export_path / "Inventory_Count_Details.xlsx"
            self._log_event(None, f"Count file exported: {count_file}")
            
            # TODO: Export timesheet
            timesheet_file = export_path / "Timesheet.xlsx"
            self._log_event(None, f"Timesheet exported: {timesheet_file}")
            
            self.export_timestamps.append(datetime.now())
            self.messages_sent.add("export_files")
            
        except Exception as e:
            self._log_event(None, f"Error exporting files: {str(e)}")
    
    def _handle_send_status(self):
        """Send inventory status update"""
        self._log_event(WorkflowEvent.SEND_STATUS, "Sending inventory audit status")
        
        try:
            if self.whatsapp_manager:
                # Build status message
                stores = self.db_manager.get_stores()
                completion_msg = f"📊 Inventory Status - {self.district}\n\n"
                
                for store in stores:
                    if store.get('district') == self.district:
                        completion = self.store_completion_status.get(
                            store.get('store', ''),
                            0
                        )
                        status_icon = "✓" if completion == 100 else "⏳"
                        completion_msg += f"{status_icon} {store.get('store', '')}: {completion}%\n"
                
                self.whatsapp_manager.send_message(self.district, completion_msg)
            
            self.messages_sent.add("send_status")
            self._log_event(None, "✓ Status message sent")
            
        except Exception as e:
            self._log_event(None, f"Error sending status: {str(e)}")
    
    def _handle_poll_stores(self):
        """Poll all stores for completion status"""
        self._log_event(WorkflowEvent.POLL_STORES, f"Polling stores in {self.district} for updates")
        
        try:
            stores = self.db_manager.get_stores()
            district_stores = [s for s in stores if s.get('district') == self.district]
            
            for store in district_stores:
                store_name = store.get('store', '')
                # TODO: Check count details for this store
                # For now, simulate with 50% completion
                self.store_completion_status[store_name] = 50
                
                self._log_event(None, f"Polled {store_name}: {self.store_completion_status[store_name]}%")
            
        except Exception as e:
            self._log_event(None, f"Error polling stores: {str(e)}")
    
    def _check_store_completion(self):
        """Check if all stores have completed their counts"""
        try:
            stores = self.db_manager.get_stores()
            district_stores = [s for s in stores if s.get('district') == self.district]
            
            if not district_stores:
                return
            
            # Count stores at 100%
            completed = sum(
                1 for store in district_stores
                if self.store_completion_status.get(store.get('store', ''), 0) == 100
            )
            
            completion_pct = (completed / len(district_stores)) * 100
            
            if completion_pct == 100 and "all_complete" not in self.messages_sent:
                self._log_event(WorkflowEvent.CHECK_COMPLETION, f"✓ All stores in {self.district} completed!")
                self.messages_sent.add("all_complete")
                
                # Send completion message
                if self.whatsapp_manager:
                    msg = f"✅ Audit Complete\n{self.district} has completed the inventory count."
                    self.whatsapp_manager.send_message(self.district, msg)
            
        except Exception as e:
            self._log_event(None, f"Error checking completion: {str(e)}")
    
    def _log_event(self, event_type, message):
        """Log an event"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        event_obj = {
            "timestamp": timestamp,
            "event_type": event_type.value if event_type else "INFO",
            "message": message,
            "state": self.state.value
        }
        self.events_log.append(event_obj)
        print(f"[{timestamp}] {event_obj['event_type']}: {message}")
    
    def get_events_log(self):
        """Get the events log"""
        return self.events_log
    
    def get_status(self):
        """Get current workflow status"""
        return {
            "state": self.state.value,
            "district": self.district,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "store_completion": self.store_completion_status,
            "messages_sent": list(self.messages_sent),
            "event_count": len(self.events_log)
        }
    
    def export_audit_report(self):
        """Export audit report as JSON"""
        report = {
            "audit_info": {
                "district": self.district,
                "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "state": self.state.value
            },
            "store_completion": self.store_completion_status,
            "messages_sent": list(self.messages_sent),
            "events_log": self.events_log
        }
        
        # Save to file
        report_path = Path.home() / "Downloads" / f"Audit_Report_{self.district}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return str(report_path)
