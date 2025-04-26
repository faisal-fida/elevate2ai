from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.services.common.logging import setup_logger
from app.services.messaging.client import MessagingClient
from app.services.messaging.state_manager import StateManager


class BaseMessageHandler(ABC):
    """Base class for message handlers"""
    
    def __init__(self, client: MessagingClient, state_manager: StateManager):
        self.client = client
        self.state_manager = state_manager
        self.logger = setup_logger(__name__)
    
    @abstractmethod
    async def handle_message(self, sender_id: str, message: str) -> Dict[str, Any]:
        """Handle an incoming message"""
        pass
    
    async def send_message(self, recipient_id: str, message: str) -> Dict[str, Any]:
        """Send a message to a recipient"""
        self.logger.info(f"Sending message to {recipient_id}: {message[:50]}...")
        return await self.client.send_message(message, recipient_id)
