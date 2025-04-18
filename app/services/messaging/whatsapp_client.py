from __future__ import annotations
from typing import Optional
import logging
from .core.messages import MessageHandler
from .core.media import MediaHandler


class WhatsApp(MessageHandler, MediaHandler):
    """Main WhatsApp class that combines all functionality for the FastAPI backend system."""

    def __init__(self, token: Optional[str] = None, phone_number_id: Optional[str] = None):
        super().__init__(token=token, phone_number_id=phone_number_id)
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(logging.NullHandler())

    async def send_message(self, phone_number: str, text: str) -> bool:
        """Sends a plain text WhatsApp message to the given phone number."""
        try:
            response = await super().send_message(message=text, recipient_id=phone_number)
            return "messages" in response
        except Exception as e:
            self.logger.error(f"Failed to send message: {str(e)}")
            return False

    async def send_media(
        self, phone_number: str, media_url: str, caption: Optional[str] = None
    ) -> bool:
        """Sends media to a phone number with an optional caption."""
        try:
            response = await self.send_media(
                phone_number=phone_number,
                media_url=media_url,
                caption=caption,
            )
            return "messages" in response
        except Exception as e:
            self.logger.error(f"Failed to send media: {str(e)}")
            return False

    def parse_incoming_message(self, data: dict) -> dict:
        """Parses a webhook payload from WhatsApp and extracts standardized fields."""
        try:
            processed_data = self.preprocess(data)
            if not processed_data.get("messages"):
                return {}

            message = processed_data["messages"][0]
            return {
                "client_id": message.get("from"),
                "phone_number": message.get("from"),
                "message_text": message.get("text", {}).get("body", ""),
                "message_type": message.get("type"),
                "message_id": message.get("id"),
                "raw_data": processed_data,
            }
        except Exception as e:
            self.logger.error(f"Failed to parse message: {str(e)}")
            return {}

    async def respond_to_client_action(self, client_id: str, action: str, context: dict) -> None:
        """Handles client actions and triggers appropriate responses."""
        messages = {
            "approve": f"Your content (ID: {context.get('post_id')}) has been approved! 🎉",
            "reject": f"Your content (ID: {context.get('post_id')}) was not approved. Please try again.",
        }
        if message := messages.get(action):
            await self.send_message(phone_number=client_id, text=message)
