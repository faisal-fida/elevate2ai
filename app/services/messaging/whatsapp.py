from __future__ import annotations
import logging
import httpx
from typing import Dict, Any, Optional, Union, List


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

    async def send_media(
        self,
        media_items: Union[Dict[str, Any], List[Dict[str, Any]]],
        phone_number: str,
        recipient_type: str = "individual",
    ) -> List[Dict[str, Any]]:
        """Send one or more media items (images/videos) to a WhatsApp user"""
        if not isinstance(media_items, list):
            media_items = [media_items]

        responses = []
        async with httpx.AsyncClient() as client:
            for item in media_items:
                media_type = item.get("type", "").lower()
                if media_type not in ["image", "video"]:
                    logging.error(f"Unsupported media type: {media_type}")
                    continue

                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": recipient_type,
                    "to": phone_number,
                    "type": media_type,
                    media_type: {"link": item.get("url", "")},
                }

                if caption := item.get("caption"):
                    payload[media_type]["caption"] = caption

                logging.info(f"Sending {media_type} to {phone_number}")
                try:
                    response = await client.post(self.url, headers=self.headers, json=payload)
                    response.raise_for_status()
                    responses.append(response.json())
                    logging.info(f"{media_type.title()} sent to {phone_number}")
                except Exception as e:
                    error_msg = f"Failed to send {media_type}: {str(e)}"
                    logging.error(error_msg)
                    responses.append({"error": error_msg})

        return responses

    async def send_interactive_buttons(
        self,
        phone_number: str,
        header_text: str,
        body_text: str,
        buttons: List[Dict[str, str]],
        recipient_type: str = "individual",
    ) -> Dict[str, Any]:
        """Send interactive buttons to a WhatsApp user

        Args:
            phone_number: The recipient's phone number
            header_text: The header text for the message
            body_text: The body text for the message
            buttons: List of button objects with 'id' and 'title' keys
            recipient_type: The recipient type (default: individual)

        Returns:
            API response as dictionary
        """
        # Format buttons according to WhatsApp API requirements
        formatted_buttons = []
        for button in buttons:
            formatted_buttons.append(
                {
                    "type": "reply",
                    "reply": {"id": button.get("id", ""), "title": button.get("title", "")},
                }
            )

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {"type": "text", "text": header_text},
                "body": {"text": body_text},
                "action": {"buttons": formatted_buttons},
            },
        }

        logging.info(f"Sending interactive buttons to {phone_number}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            logging.info(f"Interactive buttons sent to {phone_number}")
        else:
            logging.error(f"Failed to send interactive buttons to {phone_number}: {response.text}")
        return response.json()

    async def send_interactive_list(
        self,
        phone_number: str,
        header_text: str,
        body_text: str,
        button_text: str,
        sections: List[Dict[str, Any]],
        recipient_type: str = "individual",
    ) -> Dict[str, Any]:
        """Send interactive list to a WhatsApp user

        Args:
            phone_number: The recipient's phone number
            header_text: The header text for the message
            body_text: The body text for the message
            button_text: The text for the main button that opens the list
            sections: List of section objects with 'title' and 'rows' keys
            recipient_type: The recipient type (default: individual)

        Returns:
            API response as dictionary
        """
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": header_text},
                "body": {"text": body_text},
                "action": {"button": button_text, "sections": sections},
            },
        }

        logging.info(f"Sending interactive list to {phone_number}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            logging.info(f"Interactive list sent to {phone_number}")
        else:
            logging.error(f"Failed to send interactive list to {phone_number}: {response.text}")
        return response.json()
