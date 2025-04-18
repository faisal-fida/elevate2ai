from __future__ import annotations
import logging
import httpx
from typing import Dict, Any, Optional
from .base import WhatsAppBase


class MediaHandler(WhatsAppBase):
    async def send_image(
        self,
        image: str,
        recipient_id: str,
        caption: Optional[str] = None,
        recipient_type: str = "individual",
    ) -> Dict[str, Any]:
        media = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": recipient_id,
            "type": "image",
            "image": {"link": image},
        }
        if caption:
            media["image"]["caption"] = caption

        logging.info(f"Sending image to {recipient_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                headers=self.headers,
                json=media,
            )

        if response.status_code == 200:
            logging.info(f"Image sent to {recipient_id}")
        else:
            logging.error(f"Failed to send image: {response.text}")
        return response.json()
