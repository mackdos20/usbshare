import pytest
import asyncio
import websockets
import json
import logging
from common.connection import ConnectionManager
from typing import Dict, Optional
import aiohttp
from datetime import datetime
import pytest_asyncio
from cryptography.fernet import Fernet

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestServer:
    def __init__(self, host: str = "localhost", port: int = 8765, fernet_key: Optional[bytes] = None):
        self.host = host
        self.port = port
        self.server = None
        self.clients = set()
        self.message_handlers: Dict[str, callable] = {}
        self.is_running = False
        self.fernet = Fernet(fernet_key) if fernet_key else None

    async def start(self):
        """Start the WebSocket server"""
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        self.is_running = True
        logger.info(f"Server started on ws://{self.host}:{self.port}")

    async def stop(self):
        """Stop the WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.is_running = False
            logger.info("Server stopped")

    async def handle_client(self, websocket, path):
        """Handle incoming WebSocket connections"""
        self.clients.add(websocket)
        try:
            async for encrypted_message in websocket:
                try:
                    # Decrypt message
                    if self.fernet:
                        decrypted_message = self.fernet.decrypt(encrypted_message)
                        data = json.loads(decrypted_message.decode())
                    else:
                        data = json.loads(encrypted_message)
                    if 'type' in data and data['type'] in self.message_handlers:
                        await self.message_handlers[data['type']](websocket, data['data'])
                    else:
                        logger.warning(f"Unknown message type: {data.get('type')}")
                except Exception as e:
                    logger.error(f"Invalid or unhandled message received: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        finally:
            self.clients.remove(websocket)

    def register_handler(self, message_type: str, handler: callable):
        """Register a message handler"""
        self.message_handlers[message_type] = handler

    async def send_encrypted(self, websocket, message_type: str, data: dict):
        message = json.dumps({
            'type': message_type,
            'data': data
        })
        if self.fernet:
            encrypted = self.fernet.encrypt(message.encode())
            await websocket.send(encrypted)
        else:
            await websocket.send(message)

    async def broadcast(self, message_type: str, data: dict):
        """Broadcast message to all connected clients"""
        for client in self.clients:
            try:
                await self.send_encrypted(client, message_type, data)
            except websockets.exceptions.ConnectionClosed:
                continue

@pytest_asyncio.fixture
async def test_server(connection_manager):
    """Fixture to create and manage test server"""
    # Use the same Fernet key as the client for encryption
    server = TestServer(fernet_key=connection_manager.encryption_key)
    await server.start()
    yield server
    await server.stop()

@pytest_asyncio.fixture
async def connection_manager():
    """Fixture to create and manage connection manager"""
    manager = ConnectionManager()
    yield manager
    await manager.disconnect()

@pytest.mark.asyncio
async def test_basic_connection(test_server, connection_manager):
    success = await connection_manager.connect("localhost", 8765)
    assert success is True
    assert connection_manager.is_connected() is True
    info = connection_manager.get_connection_info()
    assert info['is_connected'] is True
    recv_task = asyncio.create_task(connection_manager.receive_messages())
    await asyncio.sleep(0.2)
    recv_task.cancel()

@pytest.mark.asyncio
async def test_message_exchange(test_server, connection_manager):
    received_messages = []
    async def client_handler(data):
        received_messages.append(data)
    async def server_handler(websocket, data):
        await test_server.send_encrypted(websocket, 'response', {'received': True, 'timestamp': datetime.now().isoformat()})
    connection_manager.register_handler('response', client_handler)
    test_server.register_handler('test', server_handler)
    success = await connection_manager.connect("localhost", 8765)
    assert success is True
    recv_task = asyncio.create_task(connection_manager.receive_messages())
    await asyncio.sleep(0.1)
    await connection_manager.send_message('test', {'message': 'Hello Server'})
    await asyncio.sleep(1)
    recv_task.cancel()
    assert len(received_messages) > 0
    assert received_messages[0]['received'] is True

@pytest.mark.asyncio
async def test_reconnection(test_server, connection_manager):
    success = await connection_manager.connect("localhost", 8765)
    assert success is True
    recv_task = asyncio.create_task(connection_manager.receive_messages())
    assert connection_manager.is_connected() is True
    await test_server.stop()
    await asyncio.sleep(1)
    assert connection_manager.is_connected() is False
    await test_server.start()
    await asyncio.sleep(1)
    # Reconnect
    success = await connection_manager.connect("localhost", 8765)
    assert success is True
    recv_task2 = asyncio.create_task(connection_manager.receive_messages())
    await asyncio.sleep(0.1)
    await connection_manager.send_message('test', {'message': 'Reconnect'})
    await asyncio.sleep(2)
    assert connection_manager.is_connected() is True
    recv_task.cancel()
    recv_task2.cancel()

@pytest.mark.asyncio
async def test_multiple_clients(test_server):
    clients = []
    recv_tasks = []
    messages_received = []
    for i in range(3):
        manager = ConnectionManager()
        success = await manager.connect("localhost", 8765)
        assert success is True
        recv_task = asyncio.create_task(manager.receive_messages())
        await asyncio.sleep(0.1)
        clients.append(manager)
        recv_tasks.append(recv_task)
        async def handler(data):
            messages_received.append(data)
        manager.register_handler('broadcast', handler)
    await test_server.broadcast('broadcast', {'message': 'Hello All'})
    await asyncio.sleep(1)
    for task in recv_tasks:
        task.cancel()
    assert len(messages_received) == 3
    for client in clients:
        await client.disconnect()

@pytest.mark.asyncio
async def test_large_message_handling(test_server, connection_manager):
    success = await connection_manager.connect("localhost", 8765)
    assert success is True
    recv_task = asyncio.create_task(connection_manager.receive_messages())
    await asyncio.sleep(0.1)
    large_data = {'data': 'x' * (1024 * 512)}
    try:
        await connection_manager.send_message('large', large_data)
        assert True
    except ValueError as e:
        assert "Message size exceeds maximum limit" in str(e)
    recv_task.cancel()

@pytest.mark.asyncio
async def test_error_handling(test_server, connection_manager):
    error_messages = []
    async def error_handler(data):
        error_messages.append(data)
    connection_manager.register_handler('error', error_handler)
    success = await connection_manager.connect("localhost", 8765)
    assert success is True
    recv_task = asyncio.create_task(connection_manager.receive_messages())
    await asyncio.sleep(0.1)
    await test_server.broadcast('error', {'error': 'Test Error'})
    await asyncio.sleep(1)
    recv_task.cancel()
    assert len(error_messages) > 0
    assert error_messages[0]['error'] == 'Test Error'

@pytest.mark.asyncio
async def test_connection_timeout(test_server, connection_manager):
    await test_server.stop()
    success = await connection_manager.connect("localhost", 8765)
    assert success is False
    await test_server.start()
    success = await connection_manager.connect("localhost", 8765)
    assert success is True
    recv_task = asyncio.create_task(connection_manager.receive_messages())
    await asyncio.sleep(0.2)
    recv_task.cancel()

@pytest.mark.asyncio
async def test_secure_communication(test_server, connection_manager):
    received_messages = []
    async def secure_handler(data):
        received_messages.append(data)
    connection_manager.register_handler('secure', secure_handler)
    success = await connection_manager.connect("localhost", 8765)
    assert success is True
    recv_task = asyncio.create_task(connection_manager.receive_messages())
    await asyncio.sleep(0.1)
    await connection_manager.send_message('secure', {'secret': 'encrypted_data'})
    await asyncio.sleep(1)
    recv_task.cancel()
    assert len(received_messages) > 0
    assert 'secret' in received_messages[0] 