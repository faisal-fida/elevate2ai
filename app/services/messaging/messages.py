from __future__ import annotations
import logging
import httpx
from typing import Dict, Any, Union
from .base import WhatsAppBase

class MessageHandler(WhatsAppBase):
    async def send_message(
        self, 
        message: str, 
        recipient_id: str, 
        recipient_type: str = "individual", 
        preview_url: bool = True
    ) -> Dict[str, Any]:
        """Send a text message to a WhatsApp user"""
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": recipient_id,
            "type": "text",
            "text": {"preview_url": preview_url, "body": message},
        }
        logging.info(f"Sending message to {recipient_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            logging.info(f"Message sent to {recipient_id}")
        else:
            logging.error(f"Failed to send message to {recipient_id}: {response.text}")
        return response.json()

    async def send_reaction(
        self, 
        emoji: str, 
        message_id: str, 
        recipient_id: str, 
        recipient_type: str = "individual"
    ) -> Dict[str, Any]:
        """Send a reaction to a message"""
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": recipient_id,
            "type": "reaction",
            "reaction": {"message_id": message_id, "emoji": emoji},
        }
        logging.info(f"Sending reaction to message {message_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            logging.info(f"Reaction sent to message {message_id}")
        else:
            logging.error(f"Failed to send reaction: {response.text}")
        return response.json()

    async def reply_to_message(
        self, 
        message_id: str, 
        recipient_id: str, 
        message: str, 
        preview_url: bool = True
    ) -> Dict[str, Any]:
        """Reply to a specific message"""
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "text",
            "context": {"message_id": message_id},
            "text": {"preview_url": preview_url, "body": message},
        }
        logging.info(f"Replying to message {message_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            logging.info(f"Reply sent to message {message_id}")
        else:
            logging.error(f"Failed to send reply: {response.text}")
        return response.json()

    def get_message(self, data: Dict[Any, Any]) -> Union[str, None]:
        """Extract message text from webhook data"""
        data = self.preprocess(data)
        if "messages" in data:
            return data["messages"][0]["text"]["body"]
        return None

    def get_message_type(self, data: Dict[Any, Any]) -> Union[str, None]:
        """Get message type from webhook data"""
        data = self.preprocess(data)
        if "messages" in data:
            return data["messages"][0]["type"]
        return None