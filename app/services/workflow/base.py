from abc import ABC, abstractmethod
from typing import Dict, Any
import asyncio
from app.logging import setup_logger
from app.services.messaging.client import MessagingClient
from app.services.messaging.state_manager import StateManager


class BaseWorkflow(ABC):
    """Base class for workflows"""

    def __init__(self, client: MessagingClient, state_manager: StateManager):
        self.client = client
        self.state_manager = state_manager
        self.message_queue: Dict[str, asyncio.Queue] = {}
        self.logger = setup_logger(__name__)

    def _get_message_queue(self, client_id: str) -> asyncio.Queue:
        """Get or create a message queue for the client."""
        if client_id not in self.message_queue:
            self.message_queue[client_id] = asyncio.Queue()
        return self.message_queue[client_id]

    @abstractmethod
    async def _message_processor(self, client_id: str) -> None:
        """Process messages from the queue for a specific client."""
        pass

    async def process_message(self, client_id: str, message: str) -> None:
        """Queue message for processing."""
        queue = self._get_message_queue(client_id)
        if queue.empty() and client_id not in self.state_manager.client_states:
            asyncio.create_task(self._message_processor(client_id))
        await queue.put(message)

    async def send_message(self, client_id: str, message: str) -> Dict[str, Any]:
        """Send a message to a client."""
        self.logger.info(f"Sending message to {client_id}: {message[:50]}...")
        return await self.client.send_message(message, client_id)
