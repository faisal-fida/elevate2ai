from __future__ import annotations
import logging
import httpx
from typing import Dict, Any, Optional


class WhatsApp:
    def __init__(self, token: Optional[str] = None, phone_number_id: Optional[str] = None):
        self.token = token
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v14.0"
        self.v15_base_url = "https://graph.facebook.com/v15.0"
        self.url = f"{self.base_url}/{phone_number_id}/messages"
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}
        logging.getLogger(__name__).addHandler(logging.NullHandler())

    def preprocess(self, data: Dict[Any, Any]) -> Dict[Any, Any]:
        """Preprocess webhook data before handling"""
        if data.get("object"):
            if (
                "entry" in data
                and data["entry"]
                and data["entry"][0].get("changes")
                and data["entry"][0]["changes"][0].get("value")
            ):
                return data["entry"][0]["changes"][0]["value"]
        return data

    async def send_message(
        self,
        message: str,
        phone_number: str,
        recipient_type: str = "individual",
        preview_url: bool = True,
    ) -> Dict[str, Any]:
        """Send a text message to a WhatsApp user"""
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": phone_number,
            "type": "text",
            "text": {"preview_url": preview_url, "body": message},
        }
        logging.info(f"Sending message to {phone_number}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            logging.info(f"Message sent to {phone_number}")
        else:
            logging.error(f"Failed to send message to {phone_number}: {response.text}")
        return response.json()

    async def send_image(
        self,
        image: str,
        phone_number: str,
        caption: Optional[str] = None,
        recipient_type: str = "individual",
    ) -> Dict[str, Any]:
        media = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": phone_number,
            "type": "image",
            "image": {"link": image},
        }
        if caption:
            media["image"]["caption"] = caption

        logging.info(f"Sending image to {phone_number}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=media)

        if response.status_code == 200:
            logging.info(f"Image sent to {phone_number}")
        else:
            logging.error(f"Failed to send image: {response.text}")
        return response.json()

    async def send_video(
        self,
        video: str,
        phone_number: str,
        caption: Optional[str] = None,
        recipient_type: str = "individual",
    ) -> Dict[str, Any]:
        media = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": phone_number,
            "type": "video",
            "video": {"link": video},
        }
        if caption:
            media["video"]["caption"] = caption

        logging.info(f"Sending video to {phone_number}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=media)

        if response.status_code == 200:
            logging.info(f"Video sent to {phone_number}")
        else:
            logging.error(f"Failed to send video: {response.text}")
        return response.json()
