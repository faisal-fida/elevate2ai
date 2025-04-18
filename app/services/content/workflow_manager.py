from __future__ import annotations
from typing import Dict, List
import asyncio
import logging
from dataclasses import dataclass
from app.services.messaging.whatsapp import WhatsApp
from app.services.messaging.state_manager import StateManager, WorkflowState
from .generator import ContentGenerator
from app.config import settings

MESSAGES = {
    "welcome": "👋 Welcome! Please share your promotional text and I'll help you create engaging content.",
    "start_prompt": "👋 Please start by saying 'Hi'!",
    "generating": "🎨 Generating engaging content for your promotion...",
    "approval_prompt": "Please reply with 'y' to use this content or 'n' to generate a new variation.",
    "regenerating": "🔄 Let me generate a new variation for you...",
    "invalid_choice": "Please reply with either 'y' or 'n'.",
    "finalized": "✅ Great! Your content has been finalized.",
    "error": "❌ An error occurred. Please try again.",
}


@dataclass
class WorkflowContext:
    caption: str
    image_urls: List[str]
    original_text: str


class MessageHandler:
    def __init__(
        self, whatsapp: WhatsApp, state_manager: StateManager, content_generator: ContentGenerator
    ):
        self.whatsapp = whatsapp
        self.state_manager = state_manager
        self.content_generator = content_generator

    async def _send_message(self, client_id: str, message: str) -> None:
        await self.whatsapp.send_message(phone_number=client_id, message=message)

    async def _send_content(self, client_id: str, caption: str, image_urls: List[str]) -> None:
        media_items = [{"type": "image", "url": url, "caption": caption} for url in image_urls]
        await self.whatsapp.send_media(media_items=media_items, phone_number=client_id)
        await self._send_message(client_id, MESSAGES["approval_prompt"])

    async def _generate_and_send_content(self, client_id: str, text: str) -> WorkflowContext:
        caption, image_urls = await self.content_generator.generate_content(text)
        context = WorkflowContext(caption=caption, image_urls=image_urls, original_text=text)
        await self._send_content(client_id, caption, image_urls)
        return context

    async def _send_gallery(self, client_id: str, caption: str, image_urls: List[str]) -> None:
        media_items = []
        await self._send_message(client_id, f"Here is the caption for the post: {caption}")
        await self._send_message(client_id, "Please select one of the images below:")

        # Send the media items as a gallery
        for idx, url in enumerate(image_urls, 1):
            media_items.append(
                {"type": "image", "url": url, "caption": f"Reply with {idx} to select this image."}
            )

        await self.whatsapp.send_media(media_items=media_items, phone_number=client_id)
        await asyncio.sleep(1)
        await self._send_message(
            client_id,
            "Reply with the number (1-4) to select an image, or type 'regenerate' for a new set.",
        )

    async def _generate_and_send_gallery(self, client_id: str, text: str) -> WorkflowContext:
        caption, image_urls = await self.content_generator.generate_content(text)
        context = WorkflowContext(caption=caption, image_urls=image_urls, original_text=text)
        await self._send_gallery(client_id, caption, image_urls)
        return context

    async def handle_init(self, client_id: str, message: str) -> None:
        if message.lower() == "hi":
            await self._send_message(client_id, MESSAGES["welcome"])
            self.state_manager.set_state(client_id, WorkflowState.WAITING_FOR_PROMO)
        else:
            await self._send_message(client_id, MESSAGES["start_prompt"])

    async def handle_promo_text(self, client_id: str, message: str) -> None:
        await self._send_message(client_id, MESSAGES["generating"])
        context = await self._generate_and_send_gallery(client_id, message)
        self.state_manager.set_context(client_id, vars(context))
        self.state_manager.set_state(client_id, WorkflowState.WAITING_FOR_APPROVAL)

    async def handle_approval(self, client_id: str, message: str) -> None:
        message = message.strip().lower()
        context = WorkflowContext(**self.state_manager.get_context(client_id))
        if message in {"regenerate", "n"}:
            await self._send_message(client_id, MESSAGES["regenerating"])
            new_context = await self._generate_and_send_gallery(client_id, context.original_text)
            self.state_manager.update_context(client_id, vars(new_context))
        elif message in {"1", "2", "3", "4"}:
            idx = int(message) - 1
            if 0 <= idx < len(context.image_urls):
                selected_url = context.image_urls[idx]
                await self.whatsapp.send_media(
                    media_items={"type": "image", "url": selected_url, "caption": context.caption},
                    phone_number=client_id,
                )
                await self._send_message(client_id, MESSAGES["finalized"])
                self.state_manager.reset_client(client_id)
            else:
                await self._send_message(
                    client_id, "Invalid number. Please reply with 1, 2, 3, or 4."
                )
        else:
            await self._send_message(client_id, "Please reply with 1, 2, 3, 4, or 'regenerate'.")


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
        if client_id not in self.message_queue:
            self.message_queue[client_id] = asyncio.Queue()
        return self.message_queue[client_id]

    async def _message_processor(self, client_id: str) -> None:
        queue = self._get_message_queue(client_id)
        while True:
            message = await queue.get()
            try:
                current_state = self.state_manager.get_state(client_id)
                handler = {
                    WorkflowState.INIT: self.handler.handle_init,
                    WorkflowState.WAITING_FOR_PROMO: self.handler.handle_promo_text,
                    WorkflowState.WAITING_FOR_APPROVAL: self.handler.handle_approval,
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
