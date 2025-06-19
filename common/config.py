import os
import json
import logging
import base64
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from pathlib import Path

logger = logging.getLogger('Config')

class ConfigManager:
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.path.expanduser("~"), ".usb_redirector")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.encryption_key = None
        self.config = {}
        self._initialize_config()

    def _initialize_config(self):
        """Initialize configuration"""
        try:
            # Create config directory if it doesn't exist
            os.makedirs(self.config_dir, exist_ok=True)

            # Generate encryption key if not exists
            key_file = os.path.join(self.config_dir, ".key")
            if os.path.exists(key_file):
                with open(key_file, "rb") as f:
                    self.encryption_key = f.read()
            else:
                self.encryption_key = Fernet.generate_key()
                with open(key_file, "wb") as f:
                    f.write(self.encryption_key)

            # Load or create config
            if os.path.exists(self.config_file):
                self._load_config()
            else:
                self._create_default_config()
                self._save_config()

        except Exception as e:
            logger.error(f"Error initializing config: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """Create default configuration"""
        self.config = {
            'security': {
                'tls_version': '1.3',
                'cipher_suites': [
                    'ECDHE-ECDSA-AES256-GCM-SHA384',
                    'ECDHE-RSA-AES256-GCM-SHA384'
                ],
                'certificate_path': os.path.join(self.config_dir, "certificates"),
                'key_path': os.path.join(self.config_dir, "keys")
            },
            'network': {
                'default_port': 8765,
                'proxy_enabled': False,
                'proxy_type': 'socks5',
                'proxy_host': '',
                'proxy_port': 1080,
                'proxy_username': '',
                'proxy_password': ''
            },
            'usb': {
                'allowed_devices': [],
                'blocked_devices': [],
                'stealth_mode': True,
                'process_name': 'svchost',
                'device_delay': 2.0
            },
            'logging': {
                'level': 'INFO',
                'file': os.path.join(self.config_dir, "usb_redirector.log"),
                'max_size': 10485760,  # 10MB
                'backup_count': 5
            },
            'client': {
                'auto_reconnect': True,
                'reconnect_delay': 5,
                'max_reconnect_attempts': 10
            },
            'server': {
                'max_clients': 100,
                'session_timeout': 3600,
                'heartbeat_interval': 30
            }
        }

    def _load_config(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                encrypted_data = f.read()
                decrypted_data = self._decrypt_data(encrypted_data)
                self.config = json.loads(decrypted_data)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self._create_default_config()

    def _save_config(self):
        """Save configuration to file"""
        try:
            data = json.dumps(self.config)
            encrypted_data = self._encrypt_data(data)
            with open(self.config_file, 'w') as f:
                f.write(encrypted_data)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def _encrypt_data(self, data: str) -> str:
        """Encrypt configuration data"""
        try:
            f = Fernet(self.encryption_key)
            return f.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            return data

    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt configuration data"""
        try:
            f = Fernet(self.encryption_key)
            return f.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            return encrypted_data

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        try:
            return self.config.get(section, {}).get(key, default)
        except Exception as e:
            logger.error(f"Error getting config value: {e}")
            return default

    def set(self, section: str, key: str, value: Any):
        """Set configuration value"""
        try:
            if section not in self.config:
                self.config[section] = {}
            self.config[section][key] = value
            self._save_config()
        except Exception as e:
            logger.error(f"Error setting config value: {e}")

    def get_section(self, section: str) -> Dict:
        """Get entire configuration section"""
        return self.config.get(section, {})

    def set_section(self, section: str, values: Dict):
        """Set entire configuration section"""
        try:
            self.config[section] = values
            self._save_config()
        except Exception as e:
            logger.error(f"Error setting config section: {e}")

    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self._create_default_config()
        self._save_config()

    def export_config(self, file_path: str):
        """Export configuration to file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.error(f"Error exporting config: {e}")

    def import_config(self, file_path: str):
        """Import configuration from file"""
        try:
            with open(file_path, 'r') as f:
                self.config = json.load(f)
            self._save_config()
        except Exception as e:
            logger.error(f"Error importing config: {e}") 