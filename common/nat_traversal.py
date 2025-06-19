import socket
import struct
import threading
import time
import logging
import random
from typing import Optional, Tuple

logger = logging.getLogger('NATTraversal')

class NATTraversal:
    def __init__(self):
        self.local_ip = None
        self.public_ip = None
        self.udp_socket = None
        self._stop_event = threading.Event()

    def initialize(self) -> bool:
        """Initialize NAT traversal"""
        try:
            # Create UDP socket for hole punching
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Get local IP
            self.local_ip = self._get_local_ip()
            
            # Get public IP
            self.public_ip = self._get_public_ip()
            
            return True
        except Exception as e:
            logger.error(f"Error initializing NAT traversal: {e}")
            return False

    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            # Create temporary socket to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logger.error(f"Error getting local IP: {e}")
            return '127.0.0.1'

    def _get_public_ip(self) -> str:
        """Get public IP address"""
        try:
            # Try multiple IP detection services
            services = [
                'https://api.ipify.org',
                'https://icanhazip.com',
                'https://ident.me'
            ]
            
            for service in services:
                try:
                    import urllib.request
                    with urllib.request.urlopen(service) as response:
                        return response.read().decode().strip()
                except:
                    continue
            
            return self.local_ip
        except Exception as e:
            logger.error(f"Error getting public IP: {e}")
            return self.local_ip

    def punch_hole(self, remote_ip: str, remote_port: int) -> bool:
        """Punch hole in NAT for direct connection"""
        try:
            # Send UDP packets to create hole in NAT
            for _ in range(5):
                try:
                    self.udp_socket.sendto(b'\x00', (remote_ip, remote_port))
                    time.sleep(0.1)
                except:
                    pass
            
            return True
        except Exception as e:
            logger.error(f"Error punching hole: {e}")
            return False

    def start_listening(self, port: int) -> bool:
        """Start listening for hole punching attempts"""
        try:
            self.udp_socket.bind(('0.0.0.0', port))
            
            # Start listening thread
            threading.Thread(target=self._listen_for_punches, daemon=True).start()
            
            return True
        except Exception as e:
            logger.error(f"Error starting listener: {e}")
            return False

    def _listen_for_punches(self):
        """Listen for hole punching attempts"""
        while not self._stop_event.is_set():
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                # Respond to hole punching attempt
                self.udp_socket.sendto(b'\x01', addr)
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.error(f"Error in punch listener: {e}")

    def cleanup(self):
        """Cleanup NAT traversal"""
        self._stop_event.set()
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass 