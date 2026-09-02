"""
Enhanced WhatsApp Window Management for B2B Soft Inventory Audit v2

Fixes window layout shifting when WhatsApp Desktop gets focus.

Problem:
  When _force_focus_whatsapp() runs, Windows may move/resize the audit app window
  because SetForegroundWindow() triggers window state changes in Windows.
  
Solution:
  1. Save window geometry + state BEFORE focusing WhatsApp
  2. Focus WhatsApp for message sending
  3. Restore window geometry + state AFTER WhatsApp finishes
  4. Add extra stability measures (delays, forced topmost, etc.)

Based on patterns from GFH Audit Automation (proven production code).
"""

import time
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
import sys

logger = logging.getLogger("b2bsoft.whatsapp_window")


class WindowState:
    """Capture and restore window geometry + state"""
    
    def __init__(self):
        self.geometry: str = ""
        self.state: str = "normal"
        self.x: int = 0
        self.y: int = 0
        self.width: int = 0
        self.height: int = 0
        self.is_maximized: bool = False
    
    def __bool__(self) -> bool:
        """True if state was captured"""
        return bool(self.geometry) or bool(self.state)
    
    def __repr__(self) -> str:
        return (
            f"WindowState(geometry={self.geometry!r}, state={self.state!r}, "
            f"x={self.x}, y={self.y}, w={self.width}, h={self.height}, "
            f"maximized={self.is_maximized})"
        )


class WhatsAppWindowManager:
    """
    Manages WhatsApp Desktop window focusing with stability improvements
    
    Prevents window layout shifting when focusing WhatsApp for message sending.
    Replaces simple _force_focus_whatsapp() calls with stateful management.
    """
    
    # Focus method priority (most to least reliable on Win10/11)
    FOCUS_METHODS = ["ctypes", "pygetwindow", "direct"]
    
    # Timing tuning (in seconds)
    FOCUS_DELAY = 1.0          # Wait after SetForegroundWindow
    PRE_SEND_DELAY = 0.5       # Wait before first interaction
    POST_SEND_DELAY = 0.5      # Wait after last interaction
    RESTORE_DELAY = 0.1        # Wait before restoring geometry
    
    def __init__(self, root_window=None, debug: bool = False):
        """
        Initialize WhatsApp window manager
        
        Args:
            root_window: Tkinter root (for geometry/state access)
            debug: Enable debug logging
        """
        self.root = root_window
        self.debug = debug
        self.saved_state: Optional[WindowState] = None
        self._is_whatsapp_focused = False
    
    def log(self, msg: str, level: str = "info"):
        """Log with debug prefix"""
        if self.debug:
            fn = getattr(logger, level, logger.info)
            fn(f"[WhatsApp] {msg}")
    
    # ===== Window State Capture/Restore =====
    
    def save_window_state(self) -> WindowState:
        """
        Save audit app window geometry + state before WhatsApp focus
        
        Returns:
            WindowState with captured geometry, position, size, and state
        """
        if not self.root:
            self.log("No root window provided", "warning")
            return WindowState()
        
        try:
            state = WindowState()
            
            # Capture Tkinter geometry
            state.geometry = self.root.geometry()
            self.log(f"Saved geometry: {state.geometry}")
            
            # Parse geometry: WIDTHxHEIGHT+X+Y
            try:
                geom_parts = state.geometry.split('+')
                if len(geom_parts) >= 3:
                    size_parts = geom_parts[0].split('x')
                    state.width = int(size_parts[0])
                    state.height = int(size_parts[1])
                    state.x = int(geom_parts[1])
                    state.y = int(geom_parts[2])
            except (ValueError, IndexError):
                pass
            
            # Capture window state
            try:
                state.state = self.root.state()
                state.is_maximized = (state.state == "zoomed")
                self.log(f"Saved state: {state.state} (maximized={state.is_maximized})")
            except Exception as e:
                self.log(f"Could not get window state: {e}", "warning")
                state.state = "normal"
            
            self.saved_state = state
            return state
            
        except Exception as e:
            self.log(f"Error saving window state: {e}", "error")
            return WindowState()
    
    def restore_window_state(self, state: Optional[WindowState] = None) -> bool:
        """
        Restore audit app window to saved geometry + state
        
        Called after WhatsApp finishes message sending.
        
        Args:
            state: WindowState to restore (uses self.saved_state if None)
            
        Returns:
            True if restore succeeded
        """
        if not self.root:
            self.log("No root window provided", "warning")
            return False
        
        state = state or self.saved_state
        if not state:
            self.log("No saved state to restore", "warning")
            return False
        
        try:
            # Small delay to avoid race with Windows
            time.sleep(self.RESTORE_DELAY)
            
            # Restore window state (zoomed/normal) first
            try:
                if state.is_maximized:
                    self.log("Restoring maximized state")
                    self.root.state("zoomed")
                else:
                    # Restore geometry for normal state
                    if state.geometry:
                        self.log(f"Restoring geometry: {state.geometry}")
                        self.root.geometry(state.geometry)
                    self.root.state("normal")
            except Exception as e:
                self.log(f"Error restoring state: {e}", "warning")
            
            # Bring app back to foreground
            try:
                self.log("Bringing app to foreground")
                self.root.lift()
                # Temporary "always on top" to force focus
                self.root.attributes("-topmost", True)
                self.root.after(100, lambda: self._disable_topmost())
            except Exception as e:
                self.log(f"Error lifting window: {e}", "warning")
            
            self.log("Window state restored successfully")
            return True
            
        except Exception as e:
            self.log(f"Error restoring window state: {e}", "error")
            return False
    
    def _disable_topmost(self):
        """Disable 'always on top' after focus is regained"""
        try:
            if self.root:
                self.root.attributes("-topmost", False)
                self.log("Disabled 'always on top'")
        except Exception as e:
            self.log(f"Error disabling topmost: {e}", "warning")
    
    # ===== WhatsApp Focus =====
    
    def focus_whatsapp(self, auto_restore: bool = True) -> bool:
        """
        Focus WhatsApp Desktop window with stability improvements
        
        Args:
            auto_restore: If True, restore window state after focus completes
            
        Returns:
            True if WhatsApp was successfully focused
        """
        self.log("Attempting to focus WhatsApp Desktop")
        
        # Save window state BEFORE focusing WhatsApp
        if auto_restore:
            self.save_window_state()
        
        # Try to focus WhatsApp
        success = self._focus_whatsapp_internal()
        
        if success:
            self.log("WhatsApp focused successfully")
            self._is_whatsapp_focused = True
            
            # Optional: restore immediately (some scenarios)
            # Usually you'd send messages here, then restore
        else:
            self.log("Failed to focus WhatsApp", "warning")
            # Restore immediately if focus failed
            if auto_restore:
                self.restore_window_state()
        
        return success
    
    def release_whatsapp_focus(self):
        """
        Release focus from WhatsApp and restore audit window
        
        Call this AFTER WhatsApp message sending is complete.
        """
        self.log("Releasing WhatsApp focus")
        
        if self._is_whatsapp_focused:
            # Small delay to let WhatsApp finish any pending actions
            time.sleep(self.POST_SEND_DELAY)
            
            # Restore window state
            self.restore_window_state()
            
            self._is_whatsapp_focused = False
            self.log("Focus released, window restored")
    
    def _focus_whatsapp_internal(self) -> bool:
        """
        Internal WhatsApp focus - try multiple methods in order
        
        Returns:
            True if any method succeeded
        """
        for method in self.FOCUS_METHODS:
            self.log(f"Trying focus method: {method}")
            try:
                if method == "ctypes":
                    if self._focus_with_ctypes():
                        return True
                elif method == "pygetwindow":
                    if self._focus_with_pygetwindow():
                        return True
                elif method == "direct":
                    if self._focus_direct():
                        return True
            except Exception as e:
                self.log(f"Method {method} failed: {e}", "debug")
                continue
        
        return False
    
    def _focus_with_ctypes(self) -> bool:
        """Focus WhatsApp using ctypes (Win API) — most reliable"""
        try:
            import ctypes
            import win32gui
            
            # Find WhatsApp window
            found_hwnds = []
            
            def enum_callback(hwnd, _):
                try:
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd) or ""
                        if "whatsapp" in title.lower():
                            found_hwnds.append(hwnd)
                except Exception:
                    pass
            
            win32gui.EnumWindows(enum_callback, None)
            
            if not found_hwnds:
                self.log("WhatsApp window not found (ctypes)", "debug")
                return False
            
            hwnd = found_hwnds[0]
            self.log(f"Found WhatsApp window: hwnd=0x{hwnd:X}")
            
            # Restore (show) the window
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            time.sleep(0.2)
            
            # Set foreground (focus)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            time.sleep(self.FOCUS_DELAY)
            
            self.log("Successfully focused WhatsApp via ctypes")
            return True
            
        except ImportError:
            self.log("ctypes/win32gui not available", "debug")
            return False
        except Exception as e:
            self.log(f"ctypes focus failed: {e}", "debug")
            return False
    
    def _focus_with_pygetwindow(self) -> bool:
        """Focus WhatsApp using pygetwindow — fallback to ctypes"""
        try:
            import pygetwindow as gw
            
            # Find WhatsApp windows
            windows = [
                w for w in gw.getAllWindows()
                if "whatsapp" in (w.title or "").lower()
            ]
            
            if not windows:
                self.log("WhatsApp window not found (pygetwindow)", "debug")
                return False
            
            win = windows[0]
            self.log(f"Found WhatsApp window: {win.title}")
            
            # Restore if minimized
            if win.isMinimized:
                self.log("Restoring minimized WhatsApp window")
                win.restore()
                time.sleep(0.5)
            
            # Activate (focus)
            win.activate()
            time.sleep(self.FOCUS_DELAY)
            
            self.log("Successfully focused WhatsApp via pygetwindow")
            return True
            
        except ImportError:
            self.log("pygetwindow not available", "debug")
            return False
        except Exception as e:
            self.log(f"pygetwindow focus failed: {e}", "debug")
            return False
    
    def _focus_direct(self) -> bool:
        """Direct WhatsApp launch/focus via subprocess"""
        try:
            import subprocess
            
            if sys.platform.startswith("win"):
                subprocess.Popen("start whatsapp:", shell=True)
                time.sleep(2)
                self.log("Launched WhatsApp via subprocess")
                return True
        except Exception as e:
            self.log(f"Direct focus failed: {e}", "debug")
        
        return False
    
    # ===== Context Manager Support =====
    
    def __enter__(self):
        """Context manager entry — save state"""
        self.save_window_state()
        self.focus_whatsapp(auto_restore=False)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit — restore state"""
        self.restore_window_state()
        return False


# ===== Convenience Functions =====

def focus_whatsapp_and_send(
    root_window=None,
    send_func=None,
    debug: bool = False
) -> bool:
    """
    Focus WhatsApp, run send function, restore window state
    
    Usage:
        focus_whatsapp_and_send(root, lambda: send_message())
    
    Args:
        root_window: Tkinter root window
        send_func: Callable that sends message (runs while WhatsApp is focused)
        debug: Enable debug logging
        
    Returns:
        True if send_func completed successfully
    """
    manager = WhatsAppWindowManager(root_window, debug=debug)
    
    try:
        # Focus WhatsApp
        if not manager.focus_whatsapp(auto_restore=False):
            logger.error("Failed to focus WhatsApp")
            return False
        
        # Run send function
        if send_func:
            try:
                time.sleep(manager.PRE_SEND_DELAY)
                send_func()
                logger.info("Send function completed")
            except Exception as e:
                logger.error(f"Send function failed: {e}")
                return False
        
        return True
        
    finally:
        # Always restore window state
        manager.release_whatsapp_focus()


def context_focus_whatsapp(root_window=None, debug: bool = False):
    """
    Context manager for WhatsApp focus with automatic state restoration
    
    Usage:
        with context_focus_whatsapp(root) as manager:
            # WhatsApp is focused here
            send_message()
            # Window is automatically restored on exit
    
    Args:
        root_window: Tkinter root window
        debug: Enable debug logging
        
    Returns:
        WhatsAppWindowManager context manager
    """
    return WhatsAppWindowManager(root_window, debug=debug)


# ===== Integration with existing code =====

def replace_force_focus_whatsapp(root_window):
    """
    Replace the old _force_focus_whatsapp() with new manager
    
    OLD CODE:
        self._force_focus_whatsapp()
        # Send message
        # Window might be shifted here!
    
    NEW CODE:
        manager = WhatsAppWindowManager(self)
        manager.focus_whatsapp()
        # Send message
        manager.release_whatsapp_focus()
    
    Or use context manager:
        with context_focus_whatsapp(self):
            # Send message (window automatically restored)
    """
    return WhatsAppWindowManager(root_window, debug=True)


if __name__ == "__main__":
    # Test: Print usage examples
    print(__doc__)
    print("\n=== Usage Examples ===\n")
    print("1. Function approach:")
    print("""
    manager = WhatsAppWindowManager(root_window)
    manager.focus_whatsapp()
    # ... send message ...
    manager.release_whatsapp_focus()
    """)
    print("\n2. Context manager approach:")
    print("""
    with context_focus_whatsapp(root_window) as manager:
        # WhatsApp is focused
        # ... send message ...
        # Window automatically restored on exit
    """)
    print("\n3. Convenience function:")
    print("""
    focus_whatsapp_and_send(root_window, send_func=lambda: send_message())
    """)

# Developed by Abad Umair Channa | Copyright © 2026 | All rights reserved.
