from __future__ import annotations
import httpx
from typing import Dict, Any, Optional, Union, List
from app.services.common.logging import setup_logger
from app.services.common.types import MediaItem, ButtonItem, SectionItem


class MessagingClient:
    """Base class for messaging clients"""

    def __init__(self):
        self.logger = setup_logger(__name__)

    async def send_message(self, message: str, recipient_id: str, **kwargs) -> Dict[str, Any]:
        """Send a text message to a recipient"""
        raise NotImplementedError("Subclasses must implement this method")

    async def send_media(
        self, media_items: Union[MediaItem, List[MediaItem]], recipient_id: str, **kwargs
    ) -> Dict[str, Any]:
        """Send media to a recipient"""
        raise NotImplementedError("Subclasses must implement this method")

    async def send_interactive_buttons(
        self,
        header_text: str,
        body_text: str,
        buttons: List[ButtonItem],
        recipient_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send interactive buttons to a recipient"""
        raise NotImplementedError("Subclasses must implement this method")

    async def send_interactive_list(
        self,
        header_text: str,
        body_text: str,
        button_text: str,
        sections: List[SectionItem],
        recipient_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send an interactive list to a recipient"""
        raise NotImplementedError("Subclasses must implement this method")


class WhatsApp(MessagingClient):
    """WhatsApp messaging client implementation"""

    def __init__(self, token: Optional[str] = None, phone_number_id: Optional[str] = None):
        super().__init__()
        self.token = token
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v14.0"
        self.v15_base_url = "https://graph.facebook.com/v15.0"
        self.url = f"{self.base_url}/{phone_number_id}/messages"
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}

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
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code != 200:
            self.logger.error(f"Failed to send message to {phone_number}: {response.text}")

        self.logger.info(f"Sent message to {phone_number}.")
        return response.json()

    async def send_media(
        self,
        media_items: Union[MediaItem, List[MediaItem]],
        phone_number: str,
        recipient_type: str = "individual",
    ) -> List[Dict[str, Any]]:
        """Send media to a WhatsApp user"""
        if not isinstance(media_items, list):
            media_items = [media_items]

        responses = []
        async with httpx.AsyncClient() as client:
            for item in media_items:
                media_type = item.get("type", "").lower()
                if media_type not in ["image", "video"]:
                    self.logger.error(f"Unsupported media type: {media_type}")
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

                try:
                    response = await client.post(self.url, headers=self.headers, json=payload)
                    response.raise_for_status()
                    responses.append(response.json())
                except Exception as e:
                    error_msg = f"Failed to send {media_type}: {str(e)}"
                    self.logger.error(error_msg)
                    responses.append({"error": error_msg})

        return responses

    async def send_interactive_buttons(
        self,
        header_text: str,
        body_text: str,
        buttons: List[ButtonItem],
        phone_number: str,
        recipient_type: str = "individual",
    ) -> List[Dict[str, Any]]:
        """
        Send interactive buttons to a WhatsApp user.
        If there are more than 3 buttons, automatically use interactive list instead.
        """
        # Check if buttons list is empty
        if not buttons:
            self.logger.warning("Empty buttons list provided, sending regular message instead")
            await self.send_message(
                message=f"{header_text}\n\n{body_text}",
                phone_number=phone_number,
                recipient_type=recipient_type,
            )
            return [
                {
                    "status": "success",
                    "message": "Sent as regular message due to empty buttons list",
                }
            ]

        # If more than 3 buttons, use interactive list instead
        if len(buttons) > 3:
            rows = []
            for button in buttons:
                rows.append(
                    {
                        "id": button["id"],
                        "title": button["title"],
                        "description": "",  # Optional description
                    }
                )
            section = {"title": header_text, "rows": rows}
            button_text = "Select an option"

            try:
                response = await self.send_interactive_list(
                    header_text=header_text,
                    body_text=body_text,
                    button_text=button_text,
                    sections=[section],
                    phone_number=phone_number,
                    recipient_type=recipient_type,
                )
                return [response]
            except Exception as e:
                self.logger.error(f"Error sending interactive list: {str(e)}")
                raise

        # Otherwise, use buttons as before
        responses = []
        formatted_buttons = [
            {"type": "reply", "reply": {"id": button["id"], "title": button["title"]}}
            for button in buttons
        ]

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

        self.logger.info(f"Sending interactive buttons to {phone_number}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=data)

            if response.status_code == 200:
                self.logger.info(f"Interactive buttons sent to {phone_number}")
                responses.append(response.json())
            else:
                error_msg = f"Failed to send interactive buttons to {phone_number}: {response.text}"
                self.logger.error(error_msg)
                responses.append({"error": error_msg})

        return responses

    async def send_interactive_list(
        self,
        header_text: str,
        body_text: str,
        button_text: str,
        sections: List[SectionItem],
        phone_number: str,
        recipient_type: str = "individual",
    ) -> Dict[str, Any]:
        """Send an interactive list to a WhatsApp user"""
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

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.url, headers=self.headers, json=data)

            if response.status_code == 200:
                self.logger.info(f"Interactive list sent to {phone_number}")
                return response.json()
            else:
                self.logger.error(
                    f"Failed to send interactive list to {phone_number}: {response.text}"
                )
                self.logger.error(f"Response status code: {response.status_code}")
                return {"error": response.text}
        except Exception as e:
            self.logger.error(f"Exception sending interactive list: {str(e)}")
            raise
