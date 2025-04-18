from enum import Enum
from typing import Dict
import logging
from app.services.messaging.core.base import MessagingClient, Message
from app.services.messaging.core.whatsapp import WhatsAppMessage
from .base import ContentProvider, ContentResult

logger = logging.getLogger(__name__)


class WorkflowState(str, Enum):
    INIT = "init"
    GENERATING = "generating"
    REVIEWING = "reviewing"


class ContentWorkflowManager:
    def __init__(self, messaging_client: MessagingClient, content_provider: ContentProvider):
        self.messaging_client = messaging_client
        self.content_provider = content_provider
        self.client_states: Dict[str, str] = {}
        self.pending_content: Dict[str, ContentResult] = {}

    async def handle_message(self, message: Message) -> None:
        """Handle incoming messages based on current state"""
        client_id = message.recipient_id
        state = self.client_states.get(client_id, WorkflowState.INIT)

        handlers = {
            WorkflowState.INIT: self._handle_initial_message,
            WorkflowState.GENERATING: self._handle_text_input,
            WorkflowState.REVIEWING: self._handle_review,
        }

        await handlers[state](message)

    async def _handle_initial_message(self, message: Message) -> None:
        """Handle initial interaction"""
        if message.content.lower() == "hi":
            await self._send_message(
                message.recipient_id,
                "👋 Welcome! Please share your promotional text and I'll help create engaging content.",
            )
            self.client_states[message.recipient_id] = WorkflowState.GENERATING
        else:
            await self._send_message(message.recipient_id, "👋 Please start by saying 'Hi'!")

    async def _handle_text_input(self, message: Message) -> None:
        """Handle promotional text input"""
        client_id = message.recipient_id

        await self._send_message(client_id, "🎨 Generating content...")

        try:
            content = await self.content_provider.generate_content(message.content)
            self.pending_content[client_id] = content

            # Send the generated content
            if content.image_url:
                await self.messaging_client.send_message(
                    WhatsAppMessage(
                        content=content.image_url,
                        recipient_id=client_id,
                        message_type="image",
                        caption=content.caption,
                    )
                )
            else:
                await self._send_message(client_id, content.caption)

            await self._send_message(
                client_id,
                "Please reply with 'approve' to use this content or 'reject' to generate new content.",
            )
            self.client_states[client_id] = WorkflowState.REVIEWING

        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            await self._send_message(client_id, "Sorry, I encountered an error. Please try again.")
            self.client_states[client_id] = WorkflowState.GENERATING

    async def _handle_review(self, message: Message) -> None:
        """Handle content approval/rejection"""
        client_id = message.recipient_id
        response = message.content.lower()

        if response == "approve":
            content = self.pending_content.get(client_id)
            if content:
                await self._send_message(
                    client_id, "✅ Great! Your content has been approved and is ready to use."
                )
            self._reset_client(client_id)

        elif response == "reject":
            await self._send_message(
                client_id, "Please share your promotional text again for a new variation."
            )
            self.client_states[client_id] = WorkflowState.GENERATING

        else:
            await self._send_message(client_id, "Please reply with either 'approve' or 'reject'.")

    async def _send_message(self, recipient_id: str, content: str) -> None:
        """Helper to send a text message"""
        await self.messaging_client.send_message(
            WhatsAppMessage(content=content, recipient_id=recipient_id)
        )

    def _reset_client(self, client_id: str) -> None:
        """Reset client state and content"""
        self.client_states.pop(client_id, None)
        self.pending_content.pop(client_id, None)
