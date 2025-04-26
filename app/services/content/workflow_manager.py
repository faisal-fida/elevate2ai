from __future__ import annotations
from typing import Dict
import asyncio
import logging
from app.services.messaging.whatsapp import WhatsApp
from app.services.messaging.state_manager import StateManager
from app.config import settings
from .generator import ContentGenerator
from .message_handler import MessageHandler


class ContentWorkflow:
    def __init__(self):
        self.state_manager = StateManager()
        self.content_generator = ContentGenerator()
        self.whatsapp = WhatsApp(
            token=settings.WHATSAPP_TOKEN,
            phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
        )
        self.message_queue: Dict[str, asyncio.Queue] = {}
        self.handler = MessageHandler(self.whatsapp, self.state_manager, self.content_generator)

    def _get_message_queue(self, client_id: str) -> asyncio.Queue:
        """Get or create a message queue for the client."""
        if client_id not in self.message_queue:
            self.message_queue[client_id] = asyncio.Queue()
        return self.message_queue[client_id]

    async def _message_processor(self, client_id: str) -> None:
        """Process messages from the queue for a specific client."""
        queue = self._get_message_queue(client_id)
        while True:
            message = await queue.get()
            try:
                # Process the message using the MessageHandler
                await self.handler.process_message(client_id, message)

            except Exception as e:
                logging.error(f"Error processing message for {client_id}: {e}")
            finally:
                queue.task_done()

    async def process_message(self, client_id: str, message: str) -> None:
        """Queue message for processing."""
        queue = self._get_message_queue(client_id)
        if queue.empty() and client_id not in self.state_manager.client_states:
            asyncio.create_task(self._message_processor(client_id))
        await queue.put(message)
