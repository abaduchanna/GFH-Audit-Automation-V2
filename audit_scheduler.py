#!/usr/bin/env python3
"""
Scheduler - Background workflow trigger

Monitors scheduled time and triggers audit workflow.

Usage:
    scheduler = AuditScheduler(app)
    scheduler.set_time("09:00")
    scheduler.start()
    ...
    scheduler.stop()
"""

import logging
import threading
import time
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class AuditScheduler:
    """Background scheduler for audit workflows"""
    
    def __init__(self, app, check_interval: int = 30):
        """
        Initialize scheduler
        
        Args:
            app: Main application instance (has update_status, etc.)
            check_interval: How often to check time (seconds)
        """
        self.app = app
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        
        self.scheduled_time = None
        self.enabled = False
        
        self.on_trigger = None  # Callback when time is reached
        self.last_trigger_time = None
    
    def set_time(self, time_str: str) -> bool:
        """Set trigger time (HH:MM format)"""
        try:
            # Validate format
            datetime.strptime(time_str, "%H:%M")
            self.scheduled_time = time_str
            logger.info(f"Scheduler time set to: {time_str}")
            return True
        except ValueError:
            logger.error(f"Invalid time format: {time_str}")
            return False
    
    def set_trigger_callback(self, callback: Callable):
        """Set callback to execute when time is reached"""
        self.on_trigger = callback
        logger.info("Trigger callback set")
    
    def start(self) -> bool:
        """Start scheduler background thread"""
        try:
            if self.running:
                logger.warning("Scheduler already running")
                return False
            
            self.running = True
            self.enabled = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            
            logger.info("Scheduler started")
            if self.app:
                self.app.set_status("✓ Scheduler monitoring - will trigger at " + (self.scheduled_time or "N/A"))
            return True
            
        except Exception as e:
            logger.error(f"Start error: {e}")
            return False
    
    def stop(self):
        """Stop scheduler"""
        self.running = False
        self.enabled = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        logger.info("Monitor loop started")
        
        while self.running:
            try:
                if self.enabled and self.scheduled_time:
                    now = datetime.now().strftime("%H:%M")
                    
                    # Check if time matched
                    if now == self.scheduled_time:
                        # Avoid duplicate triggers within same minute
                        if self.last_trigger_time != now:
                            logger.info(f"Trigger time {self.scheduled_time} reached!")
                            self.last_trigger_time = now
                            
                            if self.on_trigger:
                                try:
                                    self.on_trigger()
                                except Exception as e:
                                    logger.exception(f"Trigger callback error: {e}")
                            
                            # Wait remainder of minute to avoid re-trigger
                            time.sleep(60)
                
                # Check interval
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.exception(f"Monitor loop error: {e}")
                time.sleep(self.check_interval)
        
        logger.info("Monitor loop ended")
    
    def disable(self):
        """Disable scheduler without stopping"""
        self.enabled = False
        logger.info("Scheduler disabled")
        if self.app:
            self.app.set_status("✗ Scheduler disabled")
    
    def enable(self):
        """Enable scheduler"""
        self.enabled = True
        logger.info("Scheduler enabled")
        if self.app:
            self.app.set_status("✓ Scheduler enabled")


class ReminderScheduler:
    """Schedule escalation reminders at intervals"""
    
    def __init__(self, app):
        self.app = app
        self.reminders = []  # List of scheduled reminders
        self.running = False
    
    def schedule_reminders(self, base_time: datetime, interval_minutes: int = 45):
        """Schedule 3 reminders at intervals"""
        self.reminders = []
        
        for i in range(1, 4):
            reminder_time = base_time.timestamp() + (i * interval_minutes * 60)
            self.reminders.append({
                'number': i,
                'timestamp': reminder_time,
                'fired': False,
                'callback': None
            })
        
        logger.info(f"Scheduled 3 reminders at {interval_minutes}-min intervals")
    
    def set_reminder_callback(self, callback: Callable):
        """Set callback for all reminders"""
        for reminder in self.reminders:
            reminder['callback'] = callback
    
    def check_reminders(self):
        """Check if any reminders should fire"""
        now = datetime.now().timestamp()
        
        for reminder in self.reminders:
            if not reminder['fired'] and now >= reminder['timestamp']:
                logger.info(f"Firing reminder {reminder['number']}/3")
                reminder['fired'] = True
                
                if reminder['callback']:
                    try:
                        reminder['callback'](reminder['number'])
                    except Exception as e:
                        logger.exception(f"Reminder callback error: {e}")
    
    def get_unfired_count(self) -> int:
        """Get count of unfired reminders"""
        return sum(1 for r in self.reminders if not r['fired'])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test
    class MockApp:
        def set_status(self, msg):
            print(f"[STATUS] {msg}")
    
    app = MockApp()
    scheduler = AuditScheduler(app, check_interval=5)
    
    # Set trigger for 2 seconds from now
    now = datetime.now()
    trigger_time = (now.replace(second=now.second + 2)).strftime("%H:%M:%S").split(':')[0:2]
    trigger_time_str = ':'.join(trigger_time)
    
    scheduler.set_time(trigger_time_str)
    
    def on_trigger():
        print("⏰ TRIGGERED!")
    
    scheduler.set_trigger_callback(on_trigger)
    scheduler.start()
    
    # Wait for trigger
    time.sleep(70)
    scheduler.stop()
