from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
import json
import time

class MessageType(Enum):
    # Connection messages
    CONNECT = "connect"
    CONNECTION_ESTABLISHED = "connection_established"
    DISCONNECT = "disconnect"
    
    # Status messages
    STATUS_UPDATE = "status_update"
    PING = "ping"
    PONG = "pong"
    
    # Device messages
    DEVICE_LIST = "device_list"
    DEVICE_CONNECT = "device_connect"
    DEVICE_DISCONNECT = "device_disconnect"
    DEVICE_STATUS = "device_status"
    
    # Control messages
    REQUEST_CONTROL = "request_control"
    GRANT_CONTROL = "grant_control"
    REVOKE_CONTROL = "revoke_control"
    
    # Chat messages
    CHAT_MESSAGE = "chat_message"
    
    # Error messages
    ERROR = "error"

@dataclass
class Message:
    type: MessageType
    sender_id: str
    data: Dict[str, Any]
    timestamp: float = None
    recipient_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps({
            'type': self.type.value,
            'sender_id': self.sender_id,
            'data': self.data,
            'timestamp': self.timestamp,
            'recipient_id': self.recipient_id
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Create message from JSON string"""
        data = json.loads(json_str)
        return cls(
            type=MessageType(data['type']),
            sender_id=data['sender_id'],
            data=data['data'],
            timestamp=data.get('timestamp'),
            recipient_id=data.get('recipient_id')
        )

class MessageHandler:
    def __init__(self):
        self.handlers = {}
    
    def register_handler(self, message_type: MessageType, handler):
        """Register handler for message type"""
        self.handlers[message_type] = handler
    
    def create_message(self, message_type: MessageType, sender_id: str, data: Dict[str, Any], recipient_id: Optional[str] = None) -> Message:
        """Create a new message"""
        return Message(
            type=message_type,
            sender_id=sender_id,
            data=data,
            recipient_id=recipient_id
        )
    
    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle incoming message"""
        handler = self.handlers.get(message.type)
        if handler:
            return await handler(message)
        return None 