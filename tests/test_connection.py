import pytest
import asyncio
import websockets
import json
from common.connection import ConnectionManager
from unittest.mock import Mock, patch, AsyncMock
import aiohttp

@pytest.fixture
def connection_manager():
    return ConnectionManager()

@pytest.mark.asyncio
async def test_initial_state(connection_manager):
    """Test initial state of connection manager"""
    assert connection_manager.websocket is None
    assert connection_manager.connection_status is False
    assert connection_manager.wan_ip is None
    assert connection_manager.wan_port is None
    assert len(connection_manager.message_handlers) == 0

@pytest.mark.asyncio
async def test_direct_connection(connection_manager):
    """Test direct connection to server"""
    mock_ws = AsyncMock()
    with patch('websockets.connect', return_value=mock_ws):
        result = await connection_manager.connect('localhost', 8080)
        assert result is True
        assert connection_manager.connection_status is True
        assert connection_manager.websocket == mock_ws

@pytest.mark.asyncio
async def test_connection_timeout(connection_manager):
    """Test connection timeout handling"""
    with patch('websockets.connect', side_effect=asyncio.TimeoutError()):
        result = await connection_manager.connect('localhost', 8080)
        assert result is False
        assert connection_manager.connection_status is False
        assert connection_manager.websocket is None

@pytest.mark.asyncio
async def test_wan_connection(connection_manager):
    """Test WAN connection fallback"""
    mock_ws = AsyncMock()
    with patch('websockets.connect', side_effect=[asyncio.TimeoutError(), mock_ws]), \
         patch.object(connection_manager, 'get_wan_info', return_value=True):
        
        connection_manager.wan_ip = '1.2.3.4'
        connection_manager.wan_port = 1234
        
        result = await connection_manager.connect('localhost', 8080)
        assert result is True
        assert connection_manager.connection_status is True
        assert connection_manager.websocket == mock_ws

@pytest.mark.asyncio
async def test_message_sending(connection_manager):
    """Test sending encrypted messages"""
    mock_ws = AsyncMock()
    connection_manager.websocket = mock_ws
    connection_manager.connection_status = True
    
    message_type = 'test'
    data = {'key': 'value'}
    
    await connection_manager.send_message(message_type, data)
    
    # Verify message was encrypted and sent
    assert mock_ws.send.called
    sent_data = mock_ws.send.call_args[0][0]
    decrypted = connection_manager.cipher_suite.decrypt(sent_data)
    message = json.loads(decrypted.decode())
    assert message['type'] == message_type
    assert message['data'] == data

@pytest.mark.asyncio
async def test_message_receiving(connection_manager):
    """Test receiving and handling messages"""
    mock_ws = AsyncMock()
    connection_manager.websocket = mock_ws
    connection_manager.connection_status = True
    
    # Register a test handler
    handler_called = False
    async def test_handler(data):
        nonlocal handler_called
        handler_called = True
        assert data == {'key': 'value'}
    
    connection_manager.register_handler('test', test_handler)
    
    # Simulate receiving a message
    message = {
        'type': 'test',
        'data': {'key': 'value'}
    }
    encrypted_message = connection_manager.cipher_suite.encrypt(json.dumps(message).encode())
    mock_ws.recv.return_value = encrypted_message
    
    # Start message receiving loop
    task = asyncio.create_task(connection_manager.receive_messages())
    await asyncio.sleep(0.1)  # Give time for message processing
    task.cancel()
    
    assert handler_called

@pytest.mark.asyncio
async def test_disconnect(connection_manager):
    """Test disconnecting from server"""
    mock_ws = AsyncMock()
    connection_manager.websocket = mock_ws
    connection_manager.connection_status = True
    
    await connection_manager.disconnect()
    
    assert connection_manager.websocket is None
    assert connection_manager.connection_status is False
    mock_ws.close.assert_called_once()

@pytest.mark.asyncio
async def test_reconnection_logic(connection_manager):
    """Test reconnection attempts"""
    mock_ws = AsyncMock()
    with patch('websockets.connect', side_effect=[
        asyncio.TimeoutError(),
        asyncio.TimeoutError(),
        mock_ws
    ]):
        result = await connection_manager.connect('localhost', 8080)
        assert result is True
        assert connection_manager.connection_status is True
        assert connection_manager.websocket == mock_ws

@pytest.mark.asyncio
async def test_message_size_limit(connection_manager):
    """Test message size limit enforcement"""
    mock_ws = AsyncMock()
    connection_manager.websocket = mock_ws
    connection_manager.connection_status = True
    
    # Create a message that exceeds the size limit
    large_data = 'x' * (connection_manager.max_message_size + 1)
    
    with pytest.raises(ValueError):
        await connection_manager.send_message('test', {'data': large_data})

@pytest.mark.asyncio
async def test_invalid_message_format(connection_manager):
    """Test handling of invalid message format"""
    mock_ws = AsyncMock()
    connection_manager.websocket = mock_ws
    connection_manager.connection_status = True
    
    # Simulate receiving an invalid message
    invalid_message = b'invalid json'
    mock_ws.recv.return_value = invalid_message
    
    # Start message receiving loop
    task = asyncio.create_task(connection_manager.receive_messages())
    await asyncio.sleep(0.1)  # Give time for message processing
    task.cancel()
    
    # Should not raise an exception, just log warning
    assert connection_manager.connection_status is True

@pytest.mark.asyncio
async def test_wan_info_retrieval(connection_manager):
    """Test WAN information retrieval"""
    mock_ice = AsyncMock()
    mock_ice.local_candidates = [Mock(host='192.168.1.1', port=12345)]
    
    with patch('aioice.Connection', return_value=mock_ice):
        success = await connection_manager.get_wan_info()
        assert success is True
        assert connection_manager.wan_ip == '192.168.1.1'
        assert connection_manager.wan_port == 12345

@pytest.mark.asyncio
async def test_connection_flow(connection_manager):
    """Test complete connection flow"""
    mock_ws = AsyncMock()
    with patch('websockets.connect', return_value=mock_ws):
        # Test connection
        result = await connection_manager.connect('localhost', 8080)
        assert result is True
        assert connection_manager.connection_status is True
        
        # Test message sending
        await connection_manager.send_message('test', {'key': 'value'})
        assert mock_ws.send.called
        
        # Test message receiving
        message = {
            'type': 'test',
            'data': {'key': 'value'}
        }
        encrypted_message = connection_manager.cipher_suite.encrypt(json.dumps(message).encode())
        mock_ws.recv.return_value = encrypted_message
        
        handler_called = False
        async def test_handler(data):
            nonlocal handler_called
            handler_called = True
            assert data == {'key': 'value'}
        
        connection_manager.register_handler('test', test_handler)
        
        task = asyncio.create_task(connection_manager.receive_messages())
        await asyncio.sleep(0.1)
        task.cancel()
        
        assert handler_called
        
        # Test disconnection
        await connection_manager.disconnect()
        assert connection_manager.websocket is None
        assert connection_manager.connection_status is False

@pytest.mark.asyncio
async def test_message_size_validation():
    """Test message size validation"""
    manager = ConnectionManager()
    mock_websocket = AsyncMock()
    manager.websocket = mock_websocket
    
    # Create a message that exceeds the size limit
    large_data = 'x' * (manager.max_message_size + 1)
    
    with pytest.raises(ValueError):
        await manager.send_message('test', {'data': large_data})

@pytest.mark.asyncio
async def test_invalid_message_handling():
    """Test handling of invalid messages"""
    manager = ConnectionManager()
    mock_websocket = AsyncMock()
    manager.websocket = mock_websocket
    
    # Mock invalid message
    invalid_message = b'invalid message'
    mock_websocket.recv.return_value = invalid_message
    
    # Start message receiving in background
    task = asyncio.create_task(manager.receive_messages())
    await asyncio.sleep(0.1)  # Give time for message processing
    task.cancel()
    
    # Should not raise exception but log warning

@pytest.mark.asyncio
async def test_connection_info():
    """Test connection information retrieval"""
    manager = ConnectionManager()
    manager.wan_ip = '192.168.1.1'
    manager.wan_port = 12345
    manager.connection_status = True
    
    info = manager.get_connection_info()
    assert info['wan_ip'] == '192.168.1.1'
    assert info['wan_port'] == 12345
    assert info['is_connected'] is True 