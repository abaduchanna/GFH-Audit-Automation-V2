"""
Credential Manager - Handles encrypted credential storage
"""

import sqlite3
from cryptography.fernet import Fernet
from pathlib import Path
import json


class CredentialManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.cipher = self._get_or_create_cipher()
        
    def _get_or_create_cipher(self):
        """Get or create encryption cipher"""
        key_path = Path.home() / "AppData" / "Local" / "B2BSoft_Timesheet" / ".key"
        
        if key_path.exists():
            with open(key_path, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            key_path.parent.mkdir(parents=True, exist_ok=True)
            with open(key_path, 'wb') as f:
                f.write(key)
            # Set file permissions to read-only for owner
            key_path.chmod(0o600)
        
        return Fernet(key)
        
    def save_credentials(self, credentials):
        """Save credentials with encryption"""
        encrypted_creds = {}
        for key, value in credentials.items():
            if value:
                encrypted_creds[key] = self.cipher.encrypt(value.encode()).decode()
        
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete existing credentials
            cursor.execute("DELETE FROM credentials")
            
            # Insert encrypted credentials
            cursor.execute("""
                INSERT INTO credentials (access_code, account_id, username, password)
                VALUES (?, ?, ?, ?)
            """, (
                encrypted_creds.get("access_code", ""),
                encrypted_creds.get("account_id", ""),
                encrypted_creds.get("username", ""),
                encrypted_creds.get("password", "")
            ))
            
            conn.commit()
            
    def get_credentials(self):
        """Retrieve and decrypt credentials"""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT access_code, account_id, username, password FROM credentials LIMIT 1")
            row = cursor.fetchone()
            
            if not row:
                return None
            
            try:
                decrypted_creds = {
                    "access_code": self.cipher.decrypt(row[0].encode()).decode() if row[0] else "",
                    "account_id": self.cipher.decrypt(row[1].encode()).decode() if row[1] else "",
                    "username": self.cipher.decrypt(row[2].encode()).decode() if row[2] else "",
                    "password": self.cipher.decrypt(row[3].encode()).decode() if row[3] else ""
                }
                return decrypted_creds
            except Exception as e:
                print(f"Failed to decrypt credentials: {e}")
                return None
                
    def delete_credentials(self):
        """Delete all stored credentials"""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM credentials")
            conn.commit()
    
    def save_timesheet_credentials(self, credentials):
        """Save GFH Telecom timesheet credentials (encrypted)"""
        encrypted_creds = {}
        for key, value in credentials.items():
            if value:
                encrypted_creds[key] = self.cipher.encrypt(value.encode()).decode()
        
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            # Insert or update timesheet credentials
            cursor.execute("""
                INSERT OR REPLACE INTO credentials (ts_email, ts_password)
                VALUES (?, ?)
            """, (
                encrypted_creds.get("ts_email", ""),
                encrypted_creds.get("ts_password", "")
            ))
            conn.commit()
    
    def get_timesheet_credentials(self):
        """Retrieve and decrypt GFH Telecom timesheet credentials"""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ts_email, ts_password FROM credentials LIMIT 1")
            row = cursor.fetchone()
            
            if not row or (not row[0] and not row[1]):
                return None
            
            try:
                decrypted_creds = {
                    "ts_email": self.cipher.decrypt(row[0].encode()).decode() if row[0] else "",
                    "ts_password": self.cipher.decrypt(row[1].encode()).decode() if row[1] else ""
                }
                return decrypted_creds
            except Exception as e:
                print(f"Failed to decrypt timesheet credentials: {e}")
                return None
    
    def delete_timesheet_credentials(self):
        """Delete timesheet credentials"""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE credentials SET ts_email = NULL, ts_password = NULL")
            conn.commit()
