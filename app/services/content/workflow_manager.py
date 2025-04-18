from __future__ import annotations
from typing import Dict
import asyncio
import logging
from app.services.messaging.whatsapp import WhatsApp
from app.services.messaging.state_manager import StateManager, WorkflowState
from .generator import ContentGenerator
from app.config import settings


class ContentWorkflow:
    def __init__(self):
        self.state_manager = StateManager()
        self.content_generator = ContentGenerator()
        self.whatsapp = WhatsApp(
            token=settings.WHATSAPP_TOKEN,
            phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
        )
        self.message_queue: Dict[str, asyncio.Queue] = {}

    def _get_message_queue(self, client_id: str) -> asyncio.Queue:
        if client_id not in self.message_queue:
            self.message_queue[client_id] = asyncio.Queue()
        return self.message_queue[client_id]

    async def _handle_init(self, client_id: str, message: str) -> None:
        if message.lower() == "hi":
            await self.whatsapp.send_message(
                phone_number=client_id,
                message="👋 Welcome! Please share your promotional text and I'll help you create engaging content.",
            )
            self.state_manager.set_state(client_id, WorkflowState.WAITING_FOR_PROMO)
        else:
            await self.whatsapp.send_message(
                phone_number=client_id, message="👋 Please start by saying 'Hi'!"
            )

    async def _handle_promo_text(self, client_id: str, message: str) -> None:
        await self.whatsapp.send_message(
            phone_number=client_id, message="🎨 Generating engaging content for your promotion..."
        )

        caption, image_url = await self.content_generator.generate_content(message)

        self.state_manager.set_context(
            client_id,
            {
                "caption": caption,
                "image_url": image_url,
                "original_text": message,
            },
        )

        await self.whatsapp.send_image(image=image_url, phone_number=client_id, caption=caption)

        await self.whatsapp.send_message(
            phone_number=client_id,
            message="Please reply with 'y' to use this content or 'n' to generate a new variation.",
        )

        self.state_manager.set_state(client_id, WorkflowState.WAITING_FOR_APPROVAL)

    async def _handle_approval(self, client_id: str, message: str) -> None:
        """Handle client's approval or rejection of generated content."""
        message = message.lower()
        context = self.state_manager.get_context(client_id)

        if message == "y":
            await self.whatsapp.send_message(
                phone_number=client_id,
                message="✅ Great! Your content has been finalized:\n\n"
                + f"Caption: {context.get('caption')}\n"
                + f"Image URL: {context.get('image_url')}",
            )
            self.state_manager.reset_client(client_id)

        elif message == "n":
            await self.whatsapp.send_message(
                phone_number=client_id, message="🔄 Let me generate a new variation for you..."
            )

            caption, image_url = await self.content_generator.generate_content(
                context.get("original_text", "")
            )

            self.state_manager.update_context(
                client_id, {"caption": caption, "image_url": image_url}
            )

            await self.whatsapp.send_image(image=image_url, phone_number=client_id, caption=caption)

            await self.whatsapp.send_message(
                phone_number=client_id,
                message="Please reply with 'y' to use this content or 'n' to generate a new variation.",
            )

        else:
            await self.whatsapp.send_message(
                phone_number=client_id, message="Please reply with either 'y' or 'n'."
            )

    async def _message_processor(self, client_id: str) -> None:
        """Process messages in queue for a client."""
        queue = self._get_message_queue(client_id)
        while True:
            message = await queue.get()
            try:
                current_state = self.state_manager.get_state(client_id)
                handler = {
                    WorkflowState.INIT: self._handle_init,
                    WorkflowState.WAITING_FOR_PROMO: self._handle_promo_text,
                    WorkflowState.WAITING_FOR_APPROVAL: self._handle_approval,
                }.get(current_state)

                if handler:
                    await handler(client_id, message)
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
