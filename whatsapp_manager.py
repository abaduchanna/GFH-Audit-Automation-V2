"""
WhatsApp Integration for Audit Notifications
Handles sending audit messages via:
- WhatsApp Desktop (pyautogui/pynput)
- WhatsApp Web (Selenium)
"""

import time
from typing import Optional
import pyautogui
import pynput
from datetime import datetime
from pathlib import Path


class WhatsAppManager:
    """Manages WhatsApp message sending for audits"""
    
    MODE_DESKTOP = "desktop"
    MODE_WEB = "web"
    
    def __init__(self, db_manager, mode=MODE_DESKTOP):
        self.db_manager = db_manager
        self.mode = mode
        self.sent_messages = []
        self.failed_messages = []
        
    def send_message(self, district, message, retry_count=3):
        """
        Send message to district WhatsApp group
        
        Args:
            district: District name
            message: Message text
            retry_count: Number of retries on failure
        """
        try:
            # Get WhatsApp group name for district
            group_name = self._get_whatsapp_group(district)
            
            if not group_name:
                self.failed_messages.append({
                    "district": district,
                    "message": message,
                    "reason": "No WhatsApp group configured"
                })
                return False
            
            if self.mode == self.MODE_DESKTOP:
                return self._send_desktop(group_name, message, retry_count)
            elif self.mode == self.MODE_WEB:
                return self._send_web(group_name, message, retry_count)
            else:
                raise ValueError(f"Unknown mode: {self.mode}")
        
        except Exception as e:
            self.failed_messages.append({
                "district": district,
                "message": message,
                "reason": str(e)
            })
            return False
    
    def _get_whatsapp_group(self, district):
        """Get WhatsApp group name for district from database"""
        try:
            conn = self.db_manager.db_manager.connection if hasattr(self.db_manager, 'db_manager') else None
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT group_name FROM district_whatsapp_groups WHERE district = ?",
                    (district,)
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except:
            pass
        return None
    
    def _send_desktop(self, group_name, message, retry_count):
        """Send message via WhatsApp Desktop App"""
        try:
            # Bring WhatsApp to foreground
            self._activate_window("WhatsApp")
            time.sleep(1)
            
            # Search for group
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.5)
            pyautogui.typewrite(group_name, interval=0.05)
            pyautogui.press('enter')
            time.sleep(0.5)
            
            # Click on group
            pyautogui.click(100, 200)  # Approximate group list position
            time.sleep(0.5)
            
            # Click message input field
            pyautogui.click(500, 700)  # Approximate message input position
            time.sleep(0.3)
            
            # Type message (handle special characters)
            self._type_message(message)
            time.sleep(0.3)
            
            # Send (Ctrl+Enter or just Enter depending on settings)
            pyautogui.hotkey('ctrl', 'enter')
            time.sleep(1)
            
            # Log sent message
            self.sent_messages.append({
                "timestamp": datetime.now().isoformat(),
                "group": group_name,
                "message": message,
                "mode": "desktop"
            })
            
            return True
        
        except Exception as e:
            if retry_count > 0:
                time.sleep(2)
                return self._send_desktop(group_name, message, retry_count - 1)
            raise
    
    def _send_web(self, group_name, message, retry_count):
        """Send message via WhatsApp Web"""
        try:
            # Navigate to WhatsApp Web
            import webbrowser
            webbrowser.open("https://web.whatsapp.com")
            time.sleep(3)
            
            # Search for group (same as desktop)
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.5)
            pyautogui.typewrite(group_name, interval=0.05)
            pyautogui.press('enter')
            time.sleep(0.5)
            
            # Click message input
            pyautogui.click(500, 700)
            time.sleep(0.3)
            
            # Type and send
            self._type_message(message)
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(1)
            
            # Log sent message
            self.sent_messages.append({
                "timestamp": datetime.now().isoformat(),
                "group": group_name,
                "message": message,
                "mode": "web"
            })
            
            return True
        
        except Exception as e:
            if retry_count > 0:
                time.sleep(2)
                return self._send_web(group_name, message, retry_count - 1)
            raise
    
    def _type_message(self, message):
        """Type message handling special characters"""
        # Split by lines and type carefully
        lines = message.split('\n')
        for i, line in enumerate(lines):
            # Use clipboard for better compatibility
            import subprocess
            
            # Copy line to clipboard
            process = subprocess.Popen(
                ['clip'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE
            )
            process.communicate(line.encode('utf-8'))
            
            # Paste from clipboard
            pyautogui.hotkey('ctrl', 'v')
            
            # Add line break if not last line
            if i < len(lines) - 1:
                pyautogui.press('enter')
            
            time.sleep(0.2)
    
    def _activate_window(self, window_name):
        """Activate a window by name"""
        import subprocess
        try:
            # Windows: Use PowerShell to activate window
            subprocess.run([
                'powershell',
                f'Add-Type @"'
                f'using System;'
                f'using System.Runtime.InteropServices;'
                f'public class WinActivator {{'
                f'[DllImport("user32.dll")]'
                f'public static extern bool SetForegroundWindow(IntPtr hWnd);'
                f'public static void ActivateWindow(string processName) {{'
                f'var proc = System.Diagnostics.Process.GetProcessesByName(processName);'
                f'if(proc.Length > 0) SetForegroundWindow(proc[0].MainWindowHandle);'
                f'}}'
                f'}}'
                f'@"'
                f'; [WinActivator]::ActivateWindow("{window_name}")'
            ], capture_output=True)
        except:
            pass
    
    def get_sent_messages(self):
        """Get list of sent messages"""
        return self.sent_messages
    
    def get_failed_messages(self):
        """Get list of failed messages"""
        return self.failed_messages


class WhatsAppMessageQueue:
    """Queue for managing WhatsApp messages"""
    
    def __init__(self, whatsapp_manager):
        self.whatsapp_manager = whatsapp_manager
        self.message_queue = []
        self.processing = False
    
    def queue_message(self, district, message, priority=0):
        """Queue a message for sending"""
        self.message_queue.append({
            "district": district,
            "message": message,
            "priority": priority,
            "timestamp": datetime.now()
        })
        
        # Sort by priority (higher first)
        self.message_queue.sort(key=lambda x: -x['priority'])
    
    def process_queue(self):
        """Process queued messages"""
        self.processing = True
        
        while self.message_queue and self.processing:
            msg = self.message_queue.pop(0)
            
            success = self.whatsapp_manager.send_message(
                msg['district'],
                msg['message']
            )
            
            if not success:
                # Re-queue on failure
                self.queue_message(msg['district'], msg['message'], msg['priority'] - 1)
            
            time.sleep(2)  # Delay between messages
        
        self.processing = False
    
    def stop_processing(self):
        """Stop processing queue"""
        self.processing = False
    
    def clear_queue(self):
        """Clear all queued messages"""
        self.message_queue.clear()
    
    def get_queue_status(self):
        """Get current queue status"""
        return {
            "queued_messages": len(self.message_queue),
            "processing": self.processing,
            "messages": self.message_queue
        }
