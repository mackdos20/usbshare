import json
import os
import datetime
import random
import string
import hashlib
import time
import platform
import uuid
import winreg
import psutil
from pathlib import Path
import logging
import subprocess
from datetime import timedelta

logger = logging.getLogger(__name__)

class ActivationManager:
    def __init__(self):
        self.keys_file = 'activation_keys.json'
        self.used_keys_file = 'used_keys.json'
        self._ensure_files_exist()
        self._load_keys()

    def _ensure_files_exist(self):
        """Ensure required files exist"""
        if not os.path.exists(self.keys_file):
            self._generate_keys()
        if not os.path.exists(self.used_keys_file):
            with open(self.used_keys_file, 'w') as f:
                json.dump({}, f)

    def _generate_keys(self):
        """Generate 100 new activation keys"""
        keys = {}
        for _ in range(100):
            key = str(uuid.uuid4()).replace('-', '')[:16]
            formatted_key = f"{key[:4]}-{key[4:8]}-{key[8:12]}-{key[12:]}"
            keys[formatted_key] = {
                'status': 'unused',
                'created_at': datetime.datetime.now().isoformat(),
                'activation_date': None,
                'hardware_id': None,
                'expires_at': None
            }
        with open(self.keys_file, 'w') as f:
            json.dump(keys, f, indent=4)

    def _load_keys(self):
        """Load keys from files"""
        try:
            with open(self.keys_file, 'r') as f:
                self.keys = json.load(f)
            with open(self.used_keys_file, 'r') as f:
                self.used_keys = json.load(f)
        except Exception as e:
            logger.error(f"Error loading keys: {e}")
            self.keys = {}
            self.used_keys = {}

    def _save_keys(self):
        """Save keys to files"""
        try:
            with open(self.keys_file, 'w') as f:
                json.dump(self.keys, f, indent=4)
            with open(self.used_keys_file, 'w') as f:
                json.dump(self.used_keys, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving keys: {e}")

    def _get_hardware_id(self):
        """Get unique hardware ID"""
        try:
            # Get CPU info
            cpu_info = subprocess.check_output('wmic cpu get ProcessorId', shell=True).decode()
            cpu_id = cpu_info.split('\n')[1].strip()

            # Get motherboard info
            mb_info = subprocess.check_output('wmic baseboard get SerialNumber', shell=True).decode()
            mb_id = mb_info.split('\n')[1].strip()

            # Get disk info
            disk_info = subprocess.check_output('wmic diskdrive get SerialNumber', shell=True).decode()
            disk_id = disk_info.split('\n')[1].strip()

            # Combine and hash
            hw_string = f"{cpu_id}-{mb_id}-{disk_id}"
            return hashlib.sha256(hw_string.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error getting hardware ID: {e}")
            return str(uuid.uuid4())

    def _check_time_manipulation(self):
        """Check for time manipulation"""
        try:
            # Check if system time is within reasonable range
            current_year = datetime.datetime.now().year
            if current_year < 2024 or current_year > 2030:
                logger.error(f"Invalid system year: {current_year}")
                return False, "System time appears to be incorrect"

            # Create registry key if it doesn't exist
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Mack-DDoS Share") as key:
                    pass
            except Exception as e:
                logger.error(f"Error creating registry key: {e}")

            # Check registry for last validation time
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Mack-DDoS Share", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                    try:
                        last_time = winreg.QueryValueEx(key, "LastValidationTime")[0]
                        last_time = datetime.datetime.fromtimestamp(float(last_time))
                        time_diff = datetime.datetime.now() - last_time
                        
                        # If time difference is more than 24 hours, it might be manipulation
                        if time_diff.total_seconds() > 86400:
                            logger.error(f"Large time difference detected: {time_diff.total_seconds()} seconds")
                            return False, "System time appears to have been changed"
                    except:
                        # If registry value doesn't exist, create it
                        winreg.SetValueEx(key, "LastValidationTime", 0, winreg.REG_SZ, str(time.time()))
            except Exception as e:
                logger.error(f"Error accessing registry: {e}")
                # Continue without registry check if there's an error
                pass

            return True, "Time validation successful"
        except Exception as e:
            logger.error(f"Time validation error: {e}")
            return False, "Time validation failed"

    def verify_key(self, key):
        """Verify if a key is valid"""
        try:
            # Check time manipulation first
            time_valid, time_message = self._check_time_manipulation()
            if not time_valid:
                logger.error(f"Time validation failed: {time_message}")
                return False, time_message

            # Check if key exists
            if key not in self.keys:
                logger.error(f"Invalid key: {key}")
                return False, "Invalid activation key"

            key_data = self.keys[key]
            
            # Check if key is already used
            if key_data.get('status') == 'used':
                hw_id = self._get_hardware_id()
                if key_data.get('hardware_id') != hw_id:
                    logger.error(f"Key {key} is already in use on another device")
                    return False, "This key is already in use on another device"
                
                # Check if key is expired
                if key_data.get('expires_at'):
                    expires_at = datetime.datetime.fromisoformat(key_data['expires_at'])
                    if datetime.datetime.now() > expires_at:
                        logger.error(f"Key {key} has expired")
                        return False, "This key has expired"
                
                return True, "Key is valid"

            return True, "Key is valid"
        except Exception as e:
            logger.error(f"Key verification error: {e}")
            return False, "Error verifying key"

    def activate_key(self, key):
        """Activate a key"""
        try:
            # Verify key first
            is_valid, message = self.verify_key(key)
            if not is_valid:
                return False, message

            # Get hardware ID
            hw_id = self._get_hardware_id()
            now = datetime.datetime.now()
            expires_at = now + timedelta(days=30)

            # Update key status
            self.keys[key].update({
                'status': 'used',
                'activation_date': now.isoformat(),
                'hardware_id': hw_id,
                'expires_at': expires_at.isoformat()
            })

            # Save to used keys
            self.used_keys[key] = {
                'activation_date': now.isoformat(),
                'hardware_id': hw_id,
                'expires_at': expires_at.isoformat()
            }

            # Save changes
            self._save_keys()

            return True, "Key activated successfully"
        except Exception as e:
            logger.error(f"Key activation error: {e}")
            return False, "Error activating key"

    def get_remaining_days(self, key):
        """Get remaining days for a key"""
        try:
            if key not in self.keys:
                return 0

            key_data = self.keys[key]
            if key_data.get('status') != 'used' or not key_data.get('expires_at'):
                return 0

            expires_at = datetime.datetime.fromisoformat(key_data['expires_at'])
            remaining = expires_at - datetime.datetime.now()

            return max(0, remaining.days)
        except Exception as e:
            logger.error(f"Error getting remaining days: {e}")
            return 0

    def get_all_keys(self):
        """Get all keys with their status"""
        return self.keys 