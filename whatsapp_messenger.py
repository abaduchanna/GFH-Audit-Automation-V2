#!/usr/bin/env python3
"""
WhatsApp Messenger

Sends notifications via WhatsApp Web using Selenium WebDriver.

Usage:
  messenger = WhatsAppMessenger()
  success, msg = messenger.send_message(phone="923001234567", text="Test message")
  
Features:
  - Login to WhatsApp Web
  - Find contact by phone number
  - Send text messages
  - Send images with captions
  - Handle rate limiting
"""

import logging
import time
from pathlib import Path
from typing import Optional, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions

logger = logging.getLogger(__name__)


class WhatsAppMessenger:
    """WhatsApp Web messenger"""
    
    WHATSAPP_URL = "https://web.whatsapp.com"
    
    def __init__(self, headless=False, browser_profile_path: Optional[str] = None):
        """
        Initialize WhatsApp messenger
        
        Args:
            headless: Run in headless mode (no GUI)
            browser_profile_path: Path to Chrome profile with WhatsApp Web session
        """
        self.headless = headless
        self.browser_profile_path = browser_profile_path
        self.driver = None
        self.wait = None
        self.authenticated = False
        
    def _init_driver(self) -> bool:
        """Initialize Selenium Chrome driver"""
        try:
            options = ChromeOptions()
            
            if self.browser_profile_path:
                options.add_argument(f"user-data-dir={self.browser_profile_path}")
            
            if self.headless:
                options.add_argument('--headless')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 30)
            
            logger.info("Chrome driver initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize driver: {e}")
            return False
    
    def _close_driver(self):
        """Close driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def login(self) -> bool:
        """Login to WhatsApp Web"""
        try:
            logger.info("Opening WhatsApp Web...")
            self.driver.get(self.WHATSAPP_URL)
            
            # Wait for QR code or authenticated state
            try:
                # If profile exists, may be pre-authenticated
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='conversation-panel-messages']"))
                )
                logger.info("✓ Already authenticated (from profile)")
                self.authenticated = True
                return True
            except:
                pass
            
            # Wait for QR code
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='qrcode']"))
                )
                logger.info("QR code displayed - scan with your phone")
                
                # Wait for authentication (max 2 minutes)
                for _ in range(120):
                    try:
                        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='conversation-panel-messages']")
                        logger.info("✓ Authentication successful")
                        self.authenticated = True
                        return True
                    except:
                        time.sleep(1)
                
                logger.error("Authentication timeout")
                return False
                
            except Exception as e:
                logger.error(f"Login failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Login exception: {e}")
            return False
    
    def _find_contact(self, phone: str) -> bool:
        """Find contact by phone number"""
        try:
            # Click search/new chat
            search_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='search-input']"))
            )
            search_btn.click()
            
            # Type phone number
            search_btn.send_keys(phone)
            time.sleep(1)
            
            # Click first result
            first_result = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='chat-list-item-0']"))
            )
            first_result.click()
            
            logger.info(f"Found contact: {phone}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to find contact {phone}: {e}")
            return False
    
    def send_message(self, phone: str, text: str) -> Tuple[bool, str]:
        """
        Send text message
        
        Args:
            phone: Phone number (include country code, e.g., "923001234567")
            text: Message text
            
        Returns:
            (success, message)
        """
        try:
            if not self.authenticated:
                return False, "Not authenticated"
            
            # Find contact
            if not self._find_contact(phone):
                return False, "Contact not found"
            
            time.sleep(1)
            
            # Find message input box
            msg_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='msg-input']"))
            )
            
            msg_input.click()
            msg_input.send_keys(text)
            
            # Send (Ctrl+Enter or click Send button)
            msg_input.send_keys(Keys.CONTROL, Keys.RETURN)
            
            time.sleep(2)
            
            logger.info(f"✓ Message sent to {phone}")
            return True, f"Message sent to {phone}"
            
        except Exception as e:
            logger.error(f"Send message error: {e}")
            return False, f"Send error: {str(e)}"
    
    def send_image(self, phone: str, image_path: str, caption: str = "") -> Tuple[bool, str]:
        """
        Send image with optional caption
        
        Args:
            phone: Phone number
            image_path: Path to image file
            caption: Optional message caption
            
        Returns:
            (success, message)
        """
        try:
            if not self.authenticated:
                return False, "Not authenticated"
            
            if not Path(image_path).exists():
                return False, f"Image not found: {image_path}"
            
            # Find contact
            if not self._find_contact(phone):
                return False, "Contact not found"
            
            time.sleep(1)
            
            # Click attachment button
            attach_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='clip']"))
            )
            attach_btn.click()
            
            # Click "Photos & Videos"
            photo_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='media']"))
            )
            photo_btn.click()
            
            time.sleep(1)
            
            # Find file input and send file
            file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            file_input.send_keys(str(Path(image_path).absolute()))
            
            time.sleep(2)
            
            # If caption, add it
            if caption:
                caption_input = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='msg-input']")
                caption_input.send_keys(caption)
            
            # Send button
            send_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='send']"))
            )
            send_btn.click()
            
            time.sleep(2)
            
            logger.info(f"✓ Image sent to {phone}")
            return True, f"Image sent to {phone}"
            
        except Exception as e:
            logger.error(f"Send image error: {e}")
            return False, f"Send image error: {str(e)}"
    
    def __enter__(self):
        """Context manager support"""
        if self._init_driver() and self.login():
            return self
        raise RuntimeError("Failed to initialize WhatsApp messenger")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self._close_driver()


def send_whatsapp_message(
    phone: str,
    text: str,
    browser_profile: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Convenience function for sending WhatsApp messages
    
    Usage:
        success, msg = send_whatsapp_message("923001234567", "Hello")
    """
    try:
        with WhatsAppMessenger(headless=True, browser_profile_path=browser_profile) as messenger:
            return messenger.send_message(phone, text)
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        return False, str(e)


# Developed by Abad Umair Channa | Copyright © 2026 | All rights reserved.
