from __future__ import annotations
from typing import Optional
import logging
from .base import WhatsAppBase


class WhatsApp(WhatsAppBase):
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