from __future__ import annotations
from typing import Dict, Tuple
from enum import Enum
import asyncio
import logging
from heyoo.whatsapp import WhatsApp
from app.config import settings
from datetime import datetime


class WorkflowState(Enum):
    INIT = "init"
    WAITING_FOR_PROMO = "waiting_for_promo"
    WAITING_FOR_APPROVAL = "waiting_for_approval"


class ContentWorkflow:
    def __init__(self, whatsapp: WhatsApp):
        self.whatsapp = whatsapp
        self.state_handlers = {
            WorkflowState.INIT: self._handle_init,
            WorkflowState.WAITING_FOR_PROMO: self._handle_promo_text,
            WorkflowState.WAITING_FOR_APPROVAL: self._handle_approval,
        }
        self.client_states: Dict[str, WorkflowState] = {}
        self.client_contexts: Dict[str, dict] = {}
        self.message_queue: Dict[str, asyncio.Queue] = {}
        self.last_message_time: Dict[str, datetime] = {}
        self.rate_limit_delay = 1.0  # Seconds between messages

    def get_client_state(self, client_id: str) -> WorkflowState:
        return self.client_states.get(client_id, WorkflowState.INIT)

    def _get_message_queue(self, client_id: str) -> asyncio.Queue:
        """Get or create message queue for client."""
        if client_id not in self.message_queue:
            self.message_queue[client_id] = asyncio.Queue()
        return self.message_queue[client_id]

    async def _send_message(self, phone_number: str, text: str) -> None:
        """Send message with rate limiting."""
        now = datetime.now()
        if phone_number in self.last_message_time:
            time_since_last = (now - self.last_message_time[phone_number]).total_seconds()
            if time_since_last < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - time_since_last)

        await self.whatsapp.send_message(phone_number=phone_number, text=text)
        self.last_message_time[phone_number] = datetime.now()

    async def _send_media(self, phone_number: str, media_url: str, caption: str) -> None:
        """Send media with rate limiting."""
        now = datetime.now()
        if phone_number in self.last_message_time:
            time_since_last = (now - self.last_message_time[phone_number]).total_seconds()
            if time_since_last < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - time_since_last)

        await self.whatsapp.send_media(
            phone_number=phone_number, media_url=media_url, caption=caption
        )
        self.last_message_time[phone_number] = datetime.now()

    async def _message_processor(self, client_id: str) -> None:
        """Process messages in queue for a client."""
        queue = self._get_message_queue(client_id)
        while True:
            message = await queue.get()
            try:
                current_state = self.get_client_state(client_id)
                handler = self.state_handlers.get(current_state)
                if handler:
                    await handler(client_id, message)
            except Exception as e:
                logging.error(f"Error processing message for {client_id}: {e}")
            finally:
                queue.task_done()

    async def process_message(self, client_id: str, message: str) -> None:
        """Queue message for processing."""
        queue = self._get_message_queue(client_id)
        if queue.empty() and client_id not in self.client_states:
            asyncio.create_task(self._message_processor(client_id))
        await queue.put(message)

    async def _handle_init(self, client_id: str, message: str) -> None:
        """Handle initial 'Hi' message."""
        if message.lower() == "hi":
            await self._send_message(
                phone_number=client_id,
                text="👋 Welcome! Please share your promotional text and I'll help you create engaging content.",
            )
            self.client_states[client_id] = WorkflowState.WAITING_FOR_PROMO
        else:
            await self._send_message(phone_number=client_id, text="👋 Please start by saying 'Hi'!")

    async def _mock_ai_generation(self, promo_text: str) -> Tuple[str, str]:
        """Simulate AI content generation."""
        # Mock delay to simulate processing
        await asyncio.sleep(1)

        caption = f"✨ {promo_text}\n\n#trending #viral #marketing"
        image_url = "https://example.com/mock-image.jpg"
        return caption, image_url

    async def _handle_promo_text(self, client_id: str, message: str) -> None:
        """Handle promotional text input and generate content."""
        await self._send_message(
            phone_number=client_id, text="🎨 Generating engaging content for your promotion..."
        )

        caption, image_url = await self._mock_ai_generation(message)

        # Store generated content in context
        self.client_contexts[client_id] = {
            "caption": caption,
            "image_url": image_url,
            "original_text": message,
        }

        # Send preview to client
        await self._send_media(phone_number=client_id, media_url=image_url, caption=caption)

        await self._send_message(
            phone_number=client_id,
            text="Please reply with 'approve' to use this content or 'reject' to generate a new variation.",
        )

        self.client_states[client_id] = WorkflowState.WAITING_FOR_APPROVAL

    async def _handle_approval(self, client_id: str, message: str) -> None:
        """Handle client's approval or rejection of generated content."""
        message = message.lower()
        context = self.client_contexts.get(client_id, {})

        if message == "approve":
            await self._send_message(
                phone_number=client_id,
                text="✅ Great! Your content has been finalized:\n\n"
                + f"Caption: {context.get('caption')}\n"
                + f"Image URL: {context.get('image_url')}",
            )
            # Reset state
            self.client_states[client_id] = WorkflowState.INIT
            self.client_contexts.pop(client_id, None)

        elif message == "reject":
            await self._send_message(
                phone_number=client_id, text="🔄 Let me generate a new variation for you..."
            )
            # Generate new variation
            caption, image_url = await self._mock_ai_generation(context.get("original_text", ""))

            # Update context with new generation
            context.update({"caption": caption, "image_url": image_url})
            self.client_contexts[client_id] = context

            # Send new preview
            await self._send_media(phone_number=client_id, media_url=image_url, caption=caption)

            await self._send_message(
                phone_number=client_id,
                text="Please reply with 'approve' to use this content or 'reject' to generate a new variation.",
            )

        else:
            await self._send_message(
                phone_number=client_id, text="Please reply with either 'approve' or 'reject'."
            )


async def main():
    whatsapp = WhatsApp(
        token=settings.WHATSAPP_TOKEN, phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID
    )
    workflow = ContentWorkflow(whatsapp)

    # Example usage
    client_id = "923408957390"
    messages = ["Hi", "Promote our new coffee blend", "approve"]

    for message in messages:
        await workflow.process_message(client_id, message)
        await asyncio.sleep(1)  # Simulate delay between messages


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
