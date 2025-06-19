import asyncio
import ssl
import websockets
import logging
import os
from cryptography.fernet import Fernet
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json
import random
import string
import psutil
from common.messages import MessageType, Message, MessageHandler
import time
from typing import Dict, Set, Optional
from common.translator import Translator
from server.gui import ServerGUI
import socket
import requests
from common.connection import ConnectionManager
import uuid
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='server.log'
)
logger = logging.getLogger('USB_Redirector_Server')

class USBRedirectorServer:
    def __init__(self, gui=None, translator=None):
        try:
            logger.info("=== Initializing Server ===")
            logger.info(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
            self.sessions = {}
            self.encryption_key = Fernet.generate_key()
            self.cipher_suite = Fernet(self.encryption_key)
            self.process_name = self._generate_random_process_name()
            self.gui = gui
            self.message_handler = MessageHandler()
            self.connection = ConnectionManager()
            self.usb_devices: Dict[str, dict] = {}
            self._setup_message_handlers()
            self.connection_timeouts = {}
            self.max_retries = 3
            self.connection_key = None
            self.last_activity = {}
            self.connection_timeout = 60
            self.server = None
            self.is_running = False
            self.port = 8765
            self.translator = translator
            
            # Get IP addresses
            self.wan_ip = None
            self.local_ip = self.get_local_ip()
            
            # Print IP information
            logger.info("\n=== Server IP Information ===")
            logger.info(f"Local IP: {self.local_ip}")
            logger.info(f"Port: {self.port}")
            logger.info("===========================\n")
            
            self.connected_clients = set()
            logger.info("Server initialized successfully")
            logger.info("=== Server Initialization Complete ===")
            
        except Exception as e:
            error_msg = f"Error initializing server: {str(e)}"
            logger.error(error_msg)
            if self.gui:
                self.gui.show_chat_message("System", f"Error: {error_msg}")
            raise
        
    def _setup_message_handlers(self):
        """Set up message handlers"""
        self.message_handler.register_handler(MessageType.CONNECT, self._handle_connect)
        self.message_handler.register_handler(MessageType.DISCONNECT, self._handle_disconnect)
        self.message_handler.register_handler(MessageType.PING, self._handle_ping)
        self.message_handler.register_handler(MessageType.CHAT_MESSAGE, self._handle_chat_message)
        self.message_handler.register_handler(MessageType.REQUEST_CONTROL, self._handle_request_control)
        self.message_handler.register_handler(MessageType.DEVICE_LIST, self._handle_device_list)
        self.message_handler.register_handler(MessageType.DEVICE_CONNECT, self._handle_device_connect)
        self.message_handler.register_handler(MessageType.DEVICE_DISCONNECT, self._handle_device_disconnect)
        self.connection.register_handler('chat', self._handle_chat_message)
        self.connection.register_handler('request_usb_devices', self._handle_request_usb_devices)
        self.connection.register_handler('share_usb_device', self._handle_share_usb_device)

    async def handle_client(self, websocket, path):
        """Handle incoming client connections"""
        client_id = None
        client_ip = websocket.remote_address[0]
        retry_count = 0
        
        try:
            # Set up ping/pong
            websocket.ping_interval = None  # We'll handle pings manually
            
            async for message in websocket:
                try:
                    print(f"[SERVER] Received message from {client_ip}: {message[:100]}...")  # Print first 100 chars
                    msg = Message.from_json(message)
                    if not client_id and msg.type == MessageType.CONNECT:
                        client_id = msg.sender_id
                        self.connection_timeouts[client_id] = time.time()
                        print(f"[SERVER] Client {client_id} connected successfully")
                    
                    response = await self.message_handler.handle_message(msg)
                    if response:
                        try:
                            print(f"[SERVER] Sending response to {client_id}: {response.to_json()[:100]}...")
                            await websocket.send(response.to_json())
                        except websockets.exceptions.ConnectionClosed:
                            print(f"[SERVER] Failed to send response to client {client_id}")
                            break
                        
                    # Update last activity time
                    if client_id:
                        self.last_activity[client_id] = time.time()
                        
                except json.JSONDecodeError:
                    print(f"[SERVER] Invalid message format from client {client_id}")
                    continue
                except Exception as e:
                    print(f"[SERVER] Error handling message from client {client_id}: {e}")
                    if retry_count < self.max_retries:
                        retry_count += 1
                        await asyncio.sleep(1)  # Wait before retry
                        continue
                    else:
                        raise
                    
        except websockets.exceptions.ConnectionClosed as e:
            print(f"[SERVER] Client {client_id} disconnected: {e}")
            if client_id:
                await self._handle_client_disconnect(client_id, "connection_closed")
        except Exception as e:
            print(f"[SERVER] Error handling client {client_id}: {e}")
            if client_id:
                await self._handle_client_disconnect(client_id, "error")
        finally:
            if client_id in self.connection_timeouts:
                del self.connection_timeouts[client_id]
            if client_id in self.clients:
                del self.clients[client_id]
            if client_id in self.last_activity:
                del self.last_activity[client_id]

    async def _handle_client_disconnect(self, client_id: str, reason: str):
        """Handle client disconnection"""
        try:
            if client_id in self.clients:
                logger.info(f"Client {client_id} disconnected: {reason}")
                
                # Update GUI
                if self.gui:
                    self.gui.remove_client(client_id)
                
                # Clean up client data
                del self.clients[client_id]
                if client_id in self.connection_timeouts:
                    del self.connection_timeouts[client_id]
                if client_id in self.last_activity:
                    del self.last_activity[client_id]
                
                # Notify other clients
                for other_client_id in self.clients:
                    if other_client_id != client_id:
                        disconnect_message = self.message_handler.create_message(
                            MessageType.STATUS_UPDATE,
                            "server",
                            {
                                "type": "client_disconnected",
                                "client_id": client_id,
                                "reason": reason
                            },
                            other_client_id
                        )
                        try:
                            await self.clients[other_client_id].send(disconnect_message.to_json())
                        except Exception as e:
                            logger.error(f"Error notifying client {other_client_id}: {e}")
                
        except Exception as e:
            logger.error(f"Error handling client disconnect: {e}")

    async def _handle_connect(self, message: Message) -> Optional[Message]:
        """Handle client connection request"""
        try:
            client_id = message.sender_id
            print(f"[SERVER] Handling connection request from {client_id}")
            
            # Store client connection
            self.clients[client_id] = message.data.get('websocket')
            self.connection_timeouts[client_id] = time.time()
            self.last_activity[client_id] = time.time()
            
            # Update GUI
            if self.gui:
                self.gui.add_client(client_id)
                self.gui.show_chat_message("System", f"Client {client_id} connected")
            
            # Send acknowledgment
            return Message(
                type=MessageType.CONNECTION_ESTABLISHED,
                sender_id="server",
                data={"status": "connected", "client_id": client_id}
            )
        except Exception as e:
            print(f"[SERVER] Error handling connection request: {e}")
            return Message(
                type=MessageType.ERROR,
                sender_id="server",
                data={"error": str(e)}
            )

    async def _handle_disconnect(self, message: Message) -> Message:
        """Handle client disconnection"""
        client_id = message.sender_id
        if client_id in self.clients:
            if self.gui:
                self.gui.remove_client(client_id)
            del self.clients[client_id]

        return self.message_handler.create_message(
            MessageType.STATUS_UPDATE,
            "server",
            {"status": "disconnected"},
            client_id
        )

    async def _handle_status_update(self, message: Message) -> Message:
        """Handle status update from client"""
        client_id = message.sender_id
        if self.gui:
            self.gui.update_client_status(client_id, message.data.get('status'))
        
        return self.message_handler.create_message(
            MessageType.STATUS_UPDATE,
            "server",
            {"status": "received"},
            client_id
        )

    async def _handle_device_list(self, message: Message) -> Message:
        """Handle device list from client"""
        client_id = message.sender_id
        devices = message.data.get('devices', [])
        if self.gui:
            self.gui.update_client_devices(client_id, len(devices))
        
        return self.message_handler.create_message(
            MessageType.DEVICE_LIST,
            "server",
            {"status": "received"},
            client_id
        )

    async def _handle_device_connect(self, message: Message) -> Message:
        """Handle device connection request"""
        client_id = message.sender_id
        device_id = message.data.get('device_id')
        
        # Implement device connection logic
        return self.message_handler.create_message(
            MessageType.DEVICE_STATUS,
            "server",
            {"status": "connected", "device_id": device_id},
            client_id
        )

    async def _handle_device_disconnect(self, message: Message) -> Message:
        """Handle device disconnection request"""
        client_id = message.sender_id
        device_id = message.data.get('device_id')
        
        # Implement device disconnection logic
        return self.message_handler.create_message(
            MessageType.DEVICE_STATUS,
            "server",
            {"status": "disconnected", "device_id": device_id},
            client_id
        )

    async def _handle_request_control(self, message: Message) -> Message:
        """Handle control request"""
        client_id = message.sender_id
        
        # Implement control request logic
        return self.message_handler.create_message(
            MessageType.GRANT_CONTROL,
            "server",
            {"status": "granted"},
            client_id
        )

    async def _handle_chat_message(self, message: Message) -> Message:
        """Handle chat message"""
        sender_id = message.sender_id
        recipient_id = message.recipient_id
        
        if recipient_id in self.clients:
            # Forward message to recipient
            return self.message_handler.create_message(
                MessageType.CHAT_MESSAGE,
                sender_id,
                message.data,
                recipient_id
            )
        
        return self.message_handler.create_message(
            MessageType.ERROR,
            "server",
            {"error": "Recipient not found"},
            sender_id
        )

    async def _handle_ping(self, message: Message) -> Message:
        """Handle ping message"""
        return self.message_handler.create_message(
            MessageType.PONG,
            "server",
            {"timestamp": time.time()},
            message.sender_id
        )

    async def broadcast_message(self, message_type: MessageType, data: dict):
        """Broadcast message to all connected clients"""
        message = self.message_handler.create_message(message_type, "server", data)
        for client_id in self.clients:
            try:
                await self.clients[client_id].send(message.to_json())
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {e}")

    async def send_message(self, client_id: str, message_type: MessageType, data: dict):
        """Send message to specific client"""
        if client_id in self.clients:
            message = self.message_handler.create_message(message_type, "server", data, client_id)
            try:
                await self.clients[client_id].send(message.to_json())
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {e}")

    def _generate_random_process_name(self):
        """Generate a random process name for stealth"""
        common_processes = ['svchost', 'system', 'explorer', 'services']
        return random.choice(common_processes)

    def _generate_session_id(self):
        """Generate unique session ID"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    async def get_wan_ip(self) -> str:
        """Get WAN IP address"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.ipify.org') as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.warning(f"Failed to get WAN IP: {response.status}")
                        return "Unknown"
        except Exception as e:
            logger.error(f"Error getting WAN IP: {e}")
            return "Unknown"

    def get_local_ip(self):
        """Get local IP address"""
        try:
            # Try to get all network interfaces
            import ifaddr
            adapters = ifaddr.get_adapters()
            
            # First try to find a non-loopback IPv4 address that is not APIPA
            for adapter in adapters:
                for ip in adapter.ips:
                    if (ip.is_IPv4 and 
                        not ip.ip.startswith('127.') and 
                        not ip.ip.startswith('169.254.')):
                        return ip.ip
            
            # If no suitable address found, try the socket method
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Try to connect to Google's DNS server
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                return local_ip
            except Exception:
                # If that fails, try localhost
                return "127.0.0.1"
            finally:
                s.close()
        except Exception as e:
            logger.error(f"Error getting local IP: {e}")
            return "127.0.0.1"

    async def start(self):
        """Start the server"""
        try:
            logger.info("=== Starting Server ===")
            logger.info(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Get IP addresses
            self.wan_ip = await self.get_wan_ip()
            self.local_ip = self.get_local_ip()
            
            logger.info(f"WAN IP: {self.wan_ip}")
            logger.info(f"Local IP: {self.local_ip}")
            
            # Start WebSocket server
            self.server = await websockets.serve(
                self.handle_client,
                "0.0.0.0",  # Listen on all interfaces
                self.port,
                ping_interval=None,  # Disable ping to prevent connection issues
                ping_timeout=None,
                reuse_address=True,  # Allow address reuse
                close_timeout=1,  # Quick close timeout
                max_size=None,  # No message size limit
                max_queue=None,  # No queue size limit
                compression=None  # Disable compression
            )
            
            logger.info(f"Server listening on port {self.port}")
            logger.info("Server is ready to accept connections")
            
            # Update GUI with IP information
            if self.gui:
                self.gui.update_server_status(True, self.local_ip, self.port)
                self.gui.show_chat_message("System", "Server started successfully")
                self.gui.show_chat_message("System", f"Local IP: {self.local_ip}")
                self.gui.show_chat_message("System", f"WAN IP: {self.wan_ip}")
            
            logger.info("=== Server Started Successfully ===")
            
            # Keep the server running
            await asyncio.Future()  # Run forever
            
        except Exception as e:
            error_msg = f"Error starting server: {str(e)}"
            logger.error(error_msg)
            if self.gui:
                self.gui.update_server_status(False)
                self.gui.show_chat_message("System", f"Error: {error_msg}")
            raise

    async def _monitor_connections(self):
        """Monitor client connections and handle timeouts"""
        while self.is_running:
            try:
                current_time = time.time()
                disconnected_clients = []
                
                for client_id, last_time in self.last_activity.items():
                    if current_time - last_time > self.connection_timeout:
                        logger.warning(f"Client {client_id} timed out")
                        if self.gui:
                            self.gui.show_chat_message("System", f"Client {client_id} timed out")
                        disconnected_clients.append(client_id)
                
                for client_id in disconnected_clients:
                    if client_id in self.clients:
                        try:
                            await self.clients[client_id].close()
                        except Exception as e:
                            logger.error(f"Error closing connection for client {client_id}: {str(e)}")
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                error_msg = f"Error in connection monitor: {str(e)}"
                logger.error(error_msg)
                if self.gui:
                    self.gui.show_chat_message("System", f"Error: {error_msg}")
                await asyncio.sleep(1)  # Wait before retrying

    async def _handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle client connection"""
        client_id = str(uuid.uuid4())
        client_ip = websocket.remote_address[0]
        logger.info(f"=== New Connection Details ===")
        logger.info(f"Client ID: {client_id}")
        logger.info(f"Client IP: {client_ip}")
        logger.info(f"Connection Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"===========================")
        
        # Update GUI with connection info
        if self.gui:
            self.gui.show_chat_message("System", f"New connection from {client_ip} (ID: {client_id})")
        
        self.clients[client_id] = websocket
        self.connected_clients.add(client_id)
        self.last_activity[client_id] = time.time()
        
        # Send encryption key to client
        try:
            await websocket.send(self.encryption_key)
            logger.info(f"Encryption key sent to client {client_id}")
            if self.gui:
                self.gui.show_chat_message("System", f"Encryption key sent to client {client_id}")
        except Exception as e:
            error_msg = f"Error sending encryption key to client {client_id}: {str(e)}"
            logger.error(error_msg)
            if self.gui:
                self.gui.show_chat_message("System", f"Error: {error_msg}")
            return

        try:
            async for message in websocket:
                try:
                    # Log raw message
                    logger.debug(f"Raw message from client {client_id}: {message}")
                    
                    # Decrypt message
                    decrypted_message = self.cipher_suite.decrypt(message)
                    message_data = json.loads(decrypted_message.decode())
                    
                    # Log decrypted message
                    logger.debug(f"Decrypted message from client {client_id}: {message_data}")
                    
                    # Update last activity
                    self.last_activity[client_id] = time.time()
                    
                    # Handle message based on type
                    if message_data['type'] == 'chat':
                        # Log chat message
                        logger.info(f"Chat message from client {client_id}: {message_data['data']['message']}")
                        
                        # Broadcast chat message to all clients
                        for cid, client in self.clients.items():
                            if cid != client_id:  # Don't send back to sender
                                try:
                                    await client.send(message)
                                    logger.debug(f"Chat message forwarded to client {cid}")
                                except Exception as e:
                                    error_msg = f"Error sending chat message to client {cid}: {str(e)}"
                                    logger.error(error_msg)
                                    if self.gui:
                                        self.gui.show_chat_message("System", f"Error: {error_msg}")
                    
                    elif message_data['type'] == 'usb_device_list':
                        # Log USB device list update
                        logger.info(f"USB device list update from client {client_id}")
                        logger.debug(f"Device list: {message_data['data']}")
                        
                        # Handle USB device list update
                        self.usb_devices[client_id] = message_data['data']
                        # Notify technician
                        if self.gui:
                            self.gui.update_device_list(self.usb_devices)
                            self.gui.show_chat_message("System", f"USB device list updated from client {client_id}")
                    
                    elif message_data['type'] == 'usb_device_status':
                        # Log USB device status update
                        logger.info(f"USB device status update from client {client_id}")
                        logger.debug(f"Device status: {message_data['data']}")
                        
                        # Handle USB device status update
                        device_id = message_data['data']['device_id']
                        status = message_data['data']['status']
                        if client_id in self.usb_devices:
                            for device in self.usb_devices[client_id]:
                                if device['id'] == device_id:
                                    device['status'] = status
                                    break
                            # Notify technician
                            if self.gui:
                                self.gui.update_device_list(self.usb_devices)
                                self.gui.show_chat_message("System", 
                                    f"Device {device_id} status updated to {status} for client {client_id}")
                    
                    else:
                        warning_msg = f"Unknown message type from client {client_id}: {message_data['type']}"
                        logger.warning(warning_msg)
                        if self.gui:
                            self.gui.show_chat_message("System", f"Warning: {warning_msg}")
                
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid message format from client {client_id}: {str(e)}"
                    logger.error(error_msg)
                    if self.gui:
                        self.gui.show_chat_message("System", f"Error: {error_msg}")
                except Exception as e:
                    error_msg = f"Error processing message from client {client_id}: {str(e)}"
                    logger.error(error_msg)
                    if self.gui:
                        self.gui.show_chat_message("System", f"Error: {error_msg}")
                    
        except websockets.exceptions.ConnectionClosed as e:
            disconnect_msg = f"Client {client_id} disconnected: {str(e)}"
            logger.info(disconnect_msg)
            if self.gui:
                self.gui.show_chat_message("System", disconnect_msg)
        except Exception as e:
            error_msg = f"Error handling client {client_id}: {str(e)}"
            logger.error(error_msg)
            if self.gui:
                self.gui.show_chat_message("System", f"Error: {error_msg}")
        finally:
            # Log cleanup
            logger.info(f"=== Cleaning up client {client_id} ===")
            logger.info(f"Disconnection Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Cleanup
            if client_id in self.clients:
                del self.clients[client_id]
                logger.info(f"Removed client {client_id} from clients list")
            if client_id in self.connected_clients:
                self.connected_clients.remove(client_id)
                logger.info(f"Removed client {client_id} from connected clients set")
            if client_id in self.last_activity:
                del self.last_activity[client_id]
                logger.info(f"Removed client {client_id} from activity tracking")
            if client_id in self.usb_devices:
                del self.usb_devices[client_id]
                logger.info(f"Removed client {client_id} from USB devices list")
            
            # Notify technician
            if self.gui:
                self.gui.update_device_list(self.usb_devices)
                self.gui.show_chat_message("System", f"Client {client_id} cleanup completed")
            logger.info(f"=== Cleanup completed for client {client_id} ===")

    def _create_ssl_context(self):
        """Create SSL context for secure WebSocket connection"""
        try:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context
        except Exception as e:
            logger.error(f"Error creating SSL context: {e}")
            raise

    def set_gui(self, gui):
        self.gui = gui

    async def _handle_request_usb_devices(self, data: dict):
        """Handle USB device list request"""
        client_id = data['client_id']
        if client_id in self.clients:
            await self.connection.send_message('usb_device_list', {
                'devices': self.usb_devices
            })

    async def _handle_share_usb_device(self, data: dict):
        """Handle USB device sharing request"""
        client_id = data['client_id']
        device_id = data['device_id']
        if device_id in self.usb_devices:
            # Notify all clients about device sharing
            for cid, client in self.clients.items():
                if cid != client_id:
                    await self.connection.send_message('usb_device_shared', {
                        'device_id': device_id,
                        'shared_by': client_id
                    })

    def is_running(self) -> bool:
        """Check if server is running"""
        return len(self.clients) > 0

if __name__ == "__main__":
    server = USBRedirectorServer()
    asyncio.run(server.start()) 