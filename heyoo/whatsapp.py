from __future__ import annotations
from typing import Optional
import httpx
import logging
from datetime import datetime

from .core import MessageHandler, MediaHandler, TemplateHandler

class WhatsApp(MessageHandler, MediaHandler, TemplateHandler):
    """Main WhatsApp class that combines all functionality for the FastAPI backend system."""

    def __init__(self, token: Optional[str] = None, phone_number_id: Optional[str] = None):
        super().__init__(token=token, phone_number_id=phone_number_id)
        logging.getLogger(__name__).addHandler(logging.NullHandler())

    async def send_message(self, phone_number: str, text: str) -> bool:
        """Sends a plain text WhatsApp message to the given phone number."""
        try:
            response = await super().send_message(message=text, recipient_id=phone_number)
            return 'messages' in response
        except Exception as e:
            logging.error(f"Failed to send message: {str(e)}")
            return False

    async def send_media(self, phone_number: str, media_url: str, caption: Optional[str] = None) -> bool:
        """Sends media (image, video, document) to a phone number with an optional caption."""
        try:
            media_type = self._detect_media_type(media_url)
            response = await self.send_media_url(
                media_url=media_url,
                recipient_id=phone_number,
                media_type=media_type,
                caption=caption
            )
            return 'messages' in response
        except Exception as e:
            logging.error(f"Failed to send media: {str(e)}")
            return False

    def parse_incoming_message(self, data: dict) -> dict:
        """Parses a webhook payload from WhatsApp and extracts standardized fields."""
        try:
            processed_data = self.preprocess(data)
            if not processed_data.get('messages'):
                return {}

            message = processed_data['messages'][0]
            return {
                'client_id': message.get('from'),
                'phone_number': message.get('from'),
                'message_text': message.get('text', {}).get('body', ''),
                'message_type': message.get('type'),
                'message_id': message.get('id'),
                'timestamp': datetime.fromtimestamp(int(message.get('timestamp', 0))),
                'raw_data': processed_data
            }
        except Exception as e:
            logging.error(f"Failed to parse message: {str(e)}")
            return {}

    async def respond_to_client_action(self, client_id: str, action: str, context: dict) -> None:
        """Handles client actions and triggers appropriate responses."""
        try:
            if action == 'approve':
                await self.send_message(
                    phone_number=client_id,
                    text=f"Your content (ID: {context.get('post_id')}) has been approved! 🎉"
                )
            elif action == 'reject':
                await self.send_message(
                    phone_number=client_id,
                    text=f"Your content (ID: {context.get('post_id')}) was not approved. Please try again."
                )
        except Exception as e:
            logging.error(f"Failed to respond to client action: {str(e)}")

    async def trigger_content_generation(self, client_id: str, raw_message: str) -> None:
        """Handles content generation requests from clients."""
        try:
            # Send acknowledgment
            await self.send_message(
                phone_number=client_id,
                text="🎨 Processing your content request..."
            )
            
            # TODO: Implement AI content generation logic here
            # This would integrate with OpenAI or other AI services
            
            # Send a mock response for now
            await self.send_message(
                phone_number=client_id,
                text="✨ Here's your generated content draft! Please reply 'approve' to proceed."
            )
        except Exception as e:
            logging.error(f"Failed to generate content: {str(e)}")
            await self.send_message(
                phone_number=client_id,
                text="Sorry, there was an error processing your request. Please try again later."
            )

    async def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read asynchronously"""
        try:
            data = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{self.phone_number_id}/messages",
                    headers=self.headers,
                    json=data
                )
            return response.status_code == 200
        except Exception as e:
            logging.error(f"Failed to mark message as read: {str(e)}")
            return False

    def _detect_media_type(self, media_url: str) -> str:
        """Detect media type from URL extension."""
        ext = media_url.lower().split('.')[-1]
        if ext in ['jpg', 'jpeg', 'png']:
            return 'image'
        elif ext in ['mp4', 'mov']:
            return 'video'
        else:
            return 'document'

