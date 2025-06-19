import asyncio
import websockets
import ssl
import logging
import json
import os
import sys
import random
import string
from cryptography.fernet import Fernet
import usb.core
import usb.util
import psutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from common.messages import MessageType, Message, MessageHandler
import time
import uuid
from typing import Optional, TYPE_CHECKING, Dict
from common.connection import ConnectionManager
from common.translator import Translator

if TYPE_CHECKING:
    from client.gui import ClientGUI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('USB_Redirector_Client')

class USBRedirectorClient:
    def __init__(self, translator: Translator):
        try:
            logger.info("=== Initializing Client ===")
            logger.info(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            self.translator = translator
            self.websocket = None
            self.encryption_key = None
            self.cipher_suite = None
            self.usb_devices: Dict[str, dict] = {}
            self.connection_status = False
            self.gui = None
            
            logger.info("Client initialized successfully")
            logger.info("=== Client Initialization Complete ===")
            
        except Exception as e:
            error_msg = f"Error initializing client: {str(e)}"
            logger.error(error_msg)
            if self.gui:
                self.gui.show_chat_message("System", f"Error: {error_msg}")
            raise

    def _setup_message_handlers(self):
        """Setup message handlers"""
        self.connection.register_handler('chat', self._handle_chat_message)
        self.connection.register_handler('usb_device_list', self._handle_usb_device_list)
        self.connection.register_handler('usb_device_status', self._handle_usb_device_status)

    async def connect(self, host: str, port: int) -> bool:
        """Connect to server"""
        try:
            logger.info(f"=== Connecting to Server ===")
            logger.info(f"Host: {host}")
            logger.info(f"Port: {port}")
            logger.info(f"Connection Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Try localhost first if connecting to local IP
            if host in ['127.0.0.1', 'localhost']:
                try:
                    self.websocket = await websockets.connect(f'ws://localhost:{port}')
                    logger.info("Connected using localhost")
                except Exception as e:
                    logger.warning(f"Localhost connection failed: {e}")
                    # Fall back to specified host
                    self.websocket = await websockets.connect(f'ws://{host}:{port}')
            else:
                # Connect to specified host
                self.websocket = await websockets.connect(f'ws://{host}:{port}')
            
            logger.info("WebSocket connection established")
            
            # Receive encryption key from server
            self.encryption_key = await self.websocket.recv()
            self.cipher_suite = Fernet(self.encryption_key)
            logger.info("Encryption key received and initialized")
            
            # Start message receiver
            asyncio.create_task(self.receive_messages())
            logger.info("Message receiver started")
            
            # Send connection message
            await self.send_message('connect', {
                'client_id': str(uuid.uuid4()),
                'timestamp': time.time()
            })
            logger.info("Connection message sent")
            
            self.connection_status = True
            if self.gui:
                self.gui.update_connection_status(True)
                self.gui.show_chat_message("System", "Connected to server successfully")
            
            # Start ping loop to keep connection alive
            asyncio.create_task(self._ping_loop())
            
            logger.info("=== Connection Complete ===")
            return True
            
        except Exception as e:
            error_msg = f"Error connecting to server: {str(e)}"
            logger.error(error_msg)
            if self.gui:
                self.gui.update_connection_status(False)
                self.gui.show_chat_message("System", f"Error: {error_msg}")
            return False

    async def disconnect(self):
        """Disconnect from server"""
        try:
            logger.info("=== Disconnecting from Server ===")
            logger.info(f"Disconnection Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
                logger.info("WebSocket connection closed")
            
            self.connection_status = False
            if self.gui:
                self.gui.update_connection_status(False)
                self.gui.show_chat_message("System", "Disconnected from server")
            
            logger.info("=== Disconnection Complete ===")
            
        except Exception as e:
            error_msg = f"Error disconnecting from server: {str(e)}"
            logger.error(error_msg)
            if self.gui:
                self.gui.show_chat_message("System", f"Error: {error_msg}")

    async def send_message(self, message_type: str, data: dict):
        """Send an encrypted message"""
        if not self.websocket:
            error_msg = "Not connected to server"
            logger.error(error_msg)
            if self.gui:
                self.gui.show_chat_message("System", f"Error: {error_msg}")
            raise ConnectionError(error_msg)

        try:
            message = {
                'type': message_type,
                'data': data,
                'timestamp': time.time()
            }
            encrypted_message = self.cipher_suite.encrypt(json.dumps(message).encode())
            await self.websocket.send(encrypted_message)
            logger.debug(f"Message sent - Type: {message_type}, Data: {data}")
            
        except Exception as e:
            error_msg = f"Error sending message: {str(e)}"
            logger.error(error_msg)
            if self.gui:
                self.gui.show_chat_message("System", f"Error: {error_msg}")
            raise

    async def request_usb_devices(self):
        """Request list of USB devices"""
        await self.connection.send_message('request_usb_devices', {})

    async def share_usb_device(self, device_id: str):
        """Share USB device with technician"""
        await self.connection.send_message('share_usb_device', {
            'device_id': device_id
        })

    async def _handle_chat_message(self, data: dict):
        """Handle incoming chat message"""
        # This will be implemented in the GUI
        pass

    async def _handle_usb_device_list(self, data: dict):
        """Handle USB device list update"""
        self.usb_devices = data['devices']
        # This will be implemented in the GUI
        pass

    async def _handle_usb_device_status(self, data: dict):
        """Handle USB device status update"""
        device_id = data['device_id']
        status = data['status']
        if device_id in self.usb_devices:
            self.usb_devices[device_id]['status'] = status
        # This will be implemented in the GUI
        pass

    def is_connected(self) -> bool:
        """Check if connected to server"""
        return self.connection.is_connected()

    def _get_available_usb_devices(self):
        """Get list of available USB devices"""
        devices = {}
        for device in usb.core.find(find_all=True):
            try:
                device_info = {
                    'idVendor': device.idVendor,
                    'idProduct': device.idProduct,
                    'manufacturer': usb.util.get_string(device, device.iManufacturer),
                    'product': usb.util.get_string(device, device.iProduct)
                }
                devices[f"{device.idVendor}:{device.idProduct}"] = device_info
            except:
                continue
        return devices

    async def _handle_connection_established(self, message: Message):
        """Handle connection established message"""
        logger.info("Connection established with server")
        self.technician_id = message.data.get('technician_id')
        if self.gui:
            self.gui.update_connection_status("connected", self.technician_id)
        
        # Start monitoring USB devices
        self._start_usb_monitoring()

        # Start ping loop
        if self.ping_task is None or self.ping_task.done():
            self.ping_task = asyncio.create_task(self._ping_loop())

    async def _handle_status_update(self, message: Message):
        """Handle status update message"""
        status = message.data.get('status')
        if self.gui:
            self.gui.update_connection_status(status)

    async def _handle_device_status(self, message: Message):
        """Handle device status message"""
        device_id = message.data.get('device_id')
        status = message.data.get('status')
        if self.gui:
            if status == "connected":
                self.gui.add_device(device_id, "USB Device")
            else:
                self.gui.remove_device(device_id)

    async def _handle_grant_control(self, message: Message):
        """Handle control granted message"""
        if self.gui:
            self.gui.show_notification("Control granted", "The technician now has control")

    async def _handle_revoke_control(self, message: Message):
        """Handle control revoked message"""
        if self.gui:
            self.gui.show_notification("Control revoked", "The technician no longer has control")

    async def _handle_error(self, message: Message):
        """Handle error message"""
        error = message.data.get('error')
        logger.error(f"Received error from server: {error}")
        if self.gui:
            self.gui.show_error(error)
        
        if "Invalid connection key" in error:
            self.is_connected = False
            if self.gui:
                self.gui.update_connection_status("disconnected")
            raise Exception(error)

    async def _ping_loop(self):
        """Send periodic ping messages to keep connection alive"""
        while self.connection_status and self.websocket:
            try:
                await self.send_message('ping', {'timestamp': time.time()})
                await asyncio.sleep(30)  # Send ping every 30 seconds
            except Exception as e:
                logger.error(f"Error sending ping: {e}")
                self.connection_status = False
                if self.gui:
                    self.gui.update_connection_status(False)
                    self.gui.show_chat_message("System", "Connection lost. Please reconnect.")
                break
                
    async def send_chat_message(self, message: str):
        """Send chat message to technician"""
        if self.is_connected and self.technician_id:
            chat_message = self.message_handler.create_message(
                MessageType.CHAT_MESSAGE,
                self.client_id,
                {'message': message},
                self.technician_id
            )
            await self.websocket.send(chat_message.to_json())

    async def request_control(self):
        """Request control from technician"""
        if self.is_connected and self.technician_id:
            control_message = self.message_handler.create_message(
                MessageType.REQUEST_CONTROL,
                self.client_id,
                {'request': 'control'},
                self.technician_id
            )
            await self.websocket.send(control_message.to_json())

    def _create_ssl_context(self):
        """Create SSL context for secure communication"""
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        # Load SSL certificates
        # ssl_context.load_verify_locations('path/to/ca.pem')
        return ssl_context

    def _start_usb_monitoring(self):
        """Start monitoring USB devices"""
        # Implement USB device monitoring
        if self.gui:
            for device_id, device_info in self.usb_devices.items():
                self.gui.add_device(device_id, device_info['type'])

    async def receive_messages(self):
        """Receive and handle messages"""
        if not self.websocket:
            error_msg = "Not connected to server"
            logger.error(error_msg)
            if self.gui:
                self.gui.show_chat_message("System", f"Error: {error_msg}")
            raise ConnectionError(error_msg)

        try:
            logger.info("=== Starting Message Receiver ===")
            while True:
                encrypted_message = await self.websocket.recv()
                logger.debug(f"Raw message received: {encrypted_message}")
                
                decrypted_message = self.cipher_suite.decrypt(encrypted_message)
                message = json.loads(decrypted_message.decode())
                logger.debug(f"Decrypted message: {message}")

                if message['type'] == 'chat':
                    logger.info(f"Chat message received from {message.get('sender_id', 'Unknown')}")
                    if self.gui:
                        self.gui.show_chat_message(message.get('sender_id', 'Unknown'), 
                                                 message.get('data', {}).get('message', ''))
                elif message['type'] == 'usb_device_list':
                    logger.info("USB device list update received")
                    if self.gui:
                        self.gui.update_device_list(message['data'])
                elif message['type'] == 'usb_device_status':
                    logger.info(f"USB device status update received: {message['data']}")
                    if self.gui:
                        self.gui.update_device_status(message['data'])
                else:
                    warning_msg = f"Unknown message type: {message['type']}"
                    logger.warning(warning_msg)
                    if self.gui:
                        self.gui.show_chat_message("System", f"Warning: {warning_msg}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by server")
            self.connection_status = False
            if self.gui:
                self.gui.update_connection_status(False)
                self.gui.show_chat_message("System", "Connection closed by server")
        except Exception as e:
            error_msg = f"Error receiving message: {str(e)}"
            logger.error(error_msg)
            self.connection_status = False
            if self.gui:
                self.gui.update_connection_status(False)
                self.gui.show_chat_message("System", f"Error: {error_msg}")

if __name__ == "__main__":
    client = USBRedirectorClient()
    asyncio.run(client.connect()) 