from __future__ import annotations
import httpx
from typing import Dict, Any, Optional
from .base import MessagingClient, Message


class WhatsAppMessage(Message):
    """WhatsApp-specific message model"""

    preview_url: bool = True
    recipient_type: str = "individual"
    caption: Optional[str] = None


class WhatsAppClient(MessagingClient):
    def __init__(self, token: str, phone_number_id: str):
        super().__init__()
        self.token = token
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v14.0"
        self.url = f"{self.base_url}/{phone_number_id}/messages"
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}

    async def send_message(self, message: WhatsAppMessage) -> Dict[str, Any]:
        """Send a message through WhatsApp API"""
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": message.recipient_type,
            "to": message.recipient_id,
            "type": message.message_type,
        }

        if message.message_type == "text":
            data["text"] = {"preview_url": message.preview_url, "body": message.content}
        elif message.message_type == "image":
            data["image"] = {"link": message.content}
            if message.caption:
                data["image"]["caption"] = message.caption

        if message.context.get("message_id"):
            data["context"] = {"message_id": message.context["message_id"]}

        self.logger.info(f"Sending {message.message_type} to {message.recipient_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            self.logger.info(f"Message sent to {message.recipient_id}")
        else:
            self.logger.error(f"Failed to send message: {response.text}")
        return response.json()

    def extract_message(self, data: Dict[Any, Any]) -> Optional[WhatsAppMessage]:
        """Extract message from WhatsApp webhook data"""
        data = self._preprocess_webhook(data)
        if not data.get("messages"):
            return None

        msg = data["messages"][0]
        message_type = msg.get("type", "text")

        if message_type == "text":
            content = msg["text"]["body"]
        elif message_type == "image":
            content = msg["image"].get("link", "")
        else:
            self.logger.warning(f"Unsupported message type: {message_type}")
            return None

        return WhatsAppMessage(
            content=content,
            recipient_id=msg["from"],
            message_type=message_type,
            context={"message_id": msg.get("id")},
        )

    def _preprocess_webhook(self, data: Dict[Any, Any]) -> Dict[Any, Any]:
        """Preprocess webhook data"""
        if data.get("object"):
            if (
                "entry" in data
                and data["entry"]
                and data["entry"][0].get("changes")
                and data["entry"][0]["changes"][0].get("value")
            ):
                return data["entry"][0]["changes"][0]["value"]
        return data
