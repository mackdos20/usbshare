import asyncio
import websockets
import json
import logging
from cryptography.fernet import Fernet
from typing import Dict, Optional, Callable
import aioice
import socket
import requests
from asyncio import TimeoutError
import aiohttp

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.message_handlers: Dict[str, Callable] = {}
        self.connection_status = False
        self.ice_agent = None
        self.stun_servers = [
            "stun:stun.l.google.com:19302",
            "stun:stun1.l.google.com:19302",
            "stun:stun2.l.google.com:19302"
        ]
        self.turn_servers = []  # Add your TURN servers here
        self.wan_ip = None
        self.wan_port = None
        self.max_message_size = 1024 * 1024  # 1MB limit
        self.connection_timeout = 30  # 30 seconds timeout
        self.reconnect_attempts = 3
        self.reconnect_delay = 5  # seconds

    async def get_wan_info(self):
        """Get WAN IP and port information with timeout"""
        try:
            # Try to get WAN IP from STUN server with timeout
            for stun_server in self.stun_servers:
                try:
                    host, port = stun_server.split("://")[1].split(":")
                    ice = aioice.Connection(ice_controlling=True)
                    await asyncio.wait_for(
                        self._get_stun_info(ice, host, int(port)),
                        timeout=self.connection_timeout
                    )
                    return True
                except TimeoutError:
                    logger.warning(f"Timeout getting WAN info from {stun_server}")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to get WAN info from {stun_server}: {e}")
                    continue

            # Fallback to public IP service with timeout
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('https://api.ipify.org?format=json', timeout=self.connection_timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.wan_ip = data['ip']
                            return True
            except Exception as e:
                logger.error(f"Error getting WAN info from ipify: {e}")
            
            return False
        except Exception as e:
            logger.error(f"Error getting WAN info: {e}")
            return False

    async def _get_stun_info(self, ice, host, port):
        """Helper method for STUN information gathering"""
        await ice.add_local_candidate(None, "0.0.0.0", 0)
        await ice.add_remote_candidate(None, host, port)
        await ice.connect()
        self.wan_ip = ice.local_candidates[0].host
        self.wan_port = ice.local_candidates[0].port
        await ice.close()

    async def connect(self, host: str, port: int) -> bool:
        """Connect to the server with WAN support and retry mechanism"""
        for attempt in range(self.reconnect_attempts):
            try:
                # First try direct connection with timeout
                try:
                    self.websocket = await asyncio.wait_for(
                        websockets.connect(f'ws://{host}:{port}'),
                        timeout=self.connection_timeout
                    )
                    self.connection_status = True
                    return True
                except (TimeoutError, Exception) as e:
                    logger.warning(f"Direct connection attempt {attempt + 1} failed: {e}")

                # If direct connection fails, try WAN connection
                if await self.get_wan_info():
                    try:
                        self.websocket = await asyncio.wait_for(
                            websockets.connect(
                                f'ws://{self.wan_ip}:{self.wan_port}',
                                extra_headers={'X-Forwarded-For': host}
                            ),
                            timeout=self.connection_timeout
                        )
                        self.connection_status = True
                        return True
                    except (TimeoutError, Exception) as e:
                        logger.error(f"WAN connection attempt {attempt + 1} failed: {e}")

                # If both fail, try TURN servers
                for turn_server in self.turn_servers:
                    try:
                        # Implement TURN connection logic here
                        pass
                    except Exception as e:
                        logger.warning(f"TURN connection failed: {e}")
                        continue

                if attempt < self.reconnect_attempts - 1:
                    await asyncio.sleep(self.reconnect_delay)

            except Exception as e:
                logger.error(f"Connection error on attempt {attempt + 1}: {e}")
                if attempt < self.reconnect_attempts - 1:
                    await asyncio.sleep(self.reconnect_delay)

        self.connection_status = False
        return False

    async def disconnect(self):
        """Disconnect from the server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.connection_status = False
        if self.ice_agent:
            await self.ice_agent.close()
            self.ice_agent = None

    async def send_message(self, message_type: str, data: dict):
        """Send an encrypted message with validation"""
        if not self.websocket:
            raise ConnectionError("Not connected to server")

        message = {
            'type': message_type,
            'data': data
        }
        
        # Validate message size
        message_str = json.dumps(message)
        if len(message_str.encode()) > self.max_message_size:
            raise ValueError("Message size exceeds maximum limit")

        try:
            encrypted_message = self.cipher_suite.encrypt(message_str.encode())
            await self.websocket.send(encrypted_message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise

    async def receive_messages(self):
        """Receive and handle messages with reconnection logic"""
        while True:
            try:
                if not self.websocket:
                    raise ConnectionError("Not connected to server")

                encrypted_message = await self.websocket.recv()
                if len(encrypted_message) > self.max_message_size:
                    logger.warning("Received message exceeds size limit")
                    continue

                decrypted_message = self.cipher_suite.decrypt(encrypted_message)
                message = json.loads(decrypted_message.decode())

                # Validate message format
                if not isinstance(message, dict) or 'type' not in message or 'data' not in message:
                    logger.warning("Invalid message format received")
                    continue

                if message['type'] in self.message_handlers:
                    await self.message_handlers[message['type']](message['data'])
                else:
                    logger.warning(f"Unknown message type: {message['type']}")

            except websockets.exceptions.ConnectionClosed:
                logger.info("Connection closed, attempting to reconnect...")
                self.connection_status = False
                # Implement reconnection logic here
                await asyncio.sleep(self.reconnect_delay)
                continue
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                self.connection_status = False
                await asyncio.sleep(self.reconnect_delay)
                continue

    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler"""
        self.message_handlers[message_type] = handler

    def is_connected(self) -> bool:
        """Check if connected to server"""
        return self.connection_status

    def get_connection_info(self) -> dict:
        """Get connection information"""
        return {
            'wan_ip': self.wan_ip,
            'wan_port': self.wan_port,
            'is_connected': self.connection_status
        } 