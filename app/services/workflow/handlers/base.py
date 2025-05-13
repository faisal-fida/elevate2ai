from abc import ABC, abstractmethod
from typing import Dict, Any
from app.services.common.logging import setup_logger
from app.services.messaging.client import MessagingClient
from app.services.messaging.state_manager import StateManager


class BaseHandler(ABC):
    """Base class for workflow handlers"""

    def __init__(self, client: MessagingClient, state_manager: StateManager):
        self.client = client
        self.state_manager = state_manager
        self.logger = setup_logger(__name__)

    @abstractmethod
    async def handle(self, client_id: str, message: str) -> None:
        """Handle a message in the current state"""
        pass

    async def send_message(self, client_id: str, message: str) -> Dict[str, Any]:
        """Send a message to a client"""
        return await self.client.send_message(message, client_id)
