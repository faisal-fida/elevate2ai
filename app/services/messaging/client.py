"""
WhatsApp messaging client for sending different types of messages.

This module provides a client for interacting with the WhatsApp Business API,
allowing the application to send text messages, media, and interactive elements.
"""

from __future__ import annotations
import httpx
import re
from typing import Dict, Any, Optional, Union, List
from app.logging import setup_logger
from app.services.types import MediaItem, ButtonItem, SectionItem
from app.config import MEDIA_BASE_URL  # noqa: F401


class MessagingClient:
    """
    Base class for messaging clients defining the interface for sending messages.

    This abstract class defines the methods that any messaging client should implement,
    ensuring consistent behavior regardless of the underlying messaging platform.
    """

    def __init__(self):
        self.logger = setup_logger(__name__)

    async def send_message(
        self, message: str, recipient_id: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Send a text message to a recipient.

        Args:
            message: Text content to send
            recipient_id: Identifier for the message recipient
            kwargs: Additional platform-specific parameters

        Returns:
            Response data from the messaging platform
        """
        raise NotImplementedError("Subclasses must implement this method")

    async def send_media(
        self,
        media_items: Union[MediaItem, List[MediaItem]],
        recipient_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send media to a recipient.

        Args:
            media_items: Media content to send (images, videos, etc.)
            recipient_id: Identifier for the message recipient
            kwargs: Additional platform-specific parameters

        Returns:
            Response data from the messaging platform
        """
        raise NotImplementedError("Subclasses must implement this method")

    async def send_interactive_buttons(
        self,
        header_text: str,
        body_text: str,
        buttons: List[ButtonItem],
        recipient_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send interactive buttons to a recipient.

        Args:
            header_text: Text to display in the message header
            body_text: Main message content
            buttons: List of interactive buttons
            recipient_id: Identifier for the message recipient
            kwargs: Additional platform-specific parameters

        Returns:
            Response data from the messaging platform
        """
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
        """
        Send an interactive list to a recipient.

        Args:
            header_text: Text to display in the message header
            body_text: Main message content
            button_text: Text for the list button
            sections: List of sections containing selectable items
            recipient_id: Identifier for the message recipient
            kwargs: Additional platform-specific parameters

        Returns:
            Response data from the messaging platform
        """
        raise NotImplementedError("Subclasses must implement this method")


class WhatsApp(MessagingClient):
    """WhatsApp messaging client implementation using the WhatsApp Business API."""

    def __init__(
        self, token: Optional[str] = None, phone_number_id: Optional[str] = None
    ):
        super().__init__()
        self.token = token
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v14.0"
        self.v15_base_url = "https://graph.facebook.com/v15.0"
        self.url = f"{self.base_url}/{phone_number_id}/messages"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

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
        """Send a text message to a WhatsApp user."""

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": phone_number,
            "type": "text",
            "text": {"preview_url": preview_url, "body": message},
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.url, headers=self.headers, json=data)
                response_data = response.json()

                if response.status_code != 200:
                    self._handle_api_error(response_data, phone_number)
                else:
                    self.logger.info(f"Sent message to {phone_number}")

                return response_data
        except Exception as e:
            self.logger.error(f"Exception sending message to {phone_number}: {str(e)}")
            return {"error": {"message": str(e), "type": "Exception"}}

    async def send_media(
        self,
        media_items: Union[MediaItem, List[MediaItem]],
        phone_number: str,
        recipient_type: str = "individual",
    ) -> List[Dict[str, Any]]:
        """Send media to a WhatsApp user."""
        if not isinstance(media_items, list):
            media_items = [media_items]

        responses = []
        async with httpx.AsyncClient() as client:
            for item in media_items:
                response_data = await self._send_single_media_item(
                    client, item, phone_number, recipient_type
                )
                responses.append(response_data)

        return responses

    async def _send_single_media_item(
        self,
        client: httpx.AsyncClient,
        item: MediaItem,
        phone_number: str,
        recipient_type: str = "individual",
    ) -> Dict[str, Any]:
        """Send a single media item to a WhatsApp user."""

        media_type = item.get("type", "").lower()

        # Validate media type
        if media_type not in ["image", "video"]:
            self.logger.error(f"Unsupported media type: {media_type}")
            return {"error": f"Unsupported media type: {media_type}"}

        # Validate URL
        if not item.get("url"):
            self.logger.error(f"Missing URL for {media_type}")
            return {"error": f"Missing URL for {media_type}"}

        url = item.get("url")
        if url.startswith("/"):
            # url = f"{MEDIA_BASE_URL}{url}" # TODO: Uncomment this line
            url = "https://images.unsplash.com/photo-1454496522488-7a8e488e8606"
        else:
            self.logger.info(f"URL is already absolute: {url}")

        # Validate the URL format
        if not re.match(r"^https?://", url):
            self.logger.error(f"Invalid URL format: {url}")
            return {"error": f"Invalid URL format: {url}"}

        # Prepare payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": phone_number,
            "type": media_type,
            media_type: {"link": url},
        }

        # Add caption if present
        if caption := item.get("caption"):
            payload[media_type]["caption"] = caption

        try:
            self.logger.info(f"Sending {media_type} to {phone_number}")
            response = await client.post(self.url, headers=self.headers, json=payload)
            response_data = response.json()

            if response.status_code != 200:
                self._handle_api_error(response_data, phone_number, media_type)
                return {"error": self._format_error_message(response_data)}

            return response_data
        except Exception as e:
            error_msg = f"Exception sending {media_type}: {str(e)}"
            self.logger.error(error_msg)
            return {"error": {"message": error_msg, "type": "Exception"}}

    async def send_interactive_buttons(
        self,
        header_text: str,
        body_text: str,
        buttons: List[ButtonItem],
        phone_number: str,
        recipient_type: str = "individual",
    ) -> Dict[str, Any]:
        """Send interactive buttons to a WhatsApp user."""

        if len(buttons) > 3:
            return await self.send_interactive_list(
                header_text,
                body_text,
                "Select an option",
                [{"title": "Options", "items": buttons}],
                phone_number,
                recipient_type,
            )

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": btn["id"], "title": btn["title"]},
                        }
                        for btn in buttons
                    ]
                },
            },
        }

        # Add header if provided
        if header_text:
            payload["interactive"]["header"] = {"type": "text", "text": header_text}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.url, headers=self.headers, json=payload
                )
                response_data = response.json()

                if response.status_code != 200:
                    self._handle_api_error(
                        response_data, phone_number, "interactive buttons"
                    )
                else:
                    self.logger.info(f"Sent interactive buttons to {phone_number}")

                return response_data
        except Exception as e:
            error_msg = f"Exception sending interactive buttons: {str(e)}"
            self.logger.error(error_msg)
            return {"error": {"message": error_msg, "type": "Exception"}}

    async def send_interactive_list(
        self,
        header_text: str,
        body_text: str,
        button_text: str,
        sections: List[SectionItem],
        phone_number: str,
        recipient_type: str = "individual",
    ) -> Dict[str, Any]:
        """Send an interactive list to a WhatsApp user."""

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body_text},
                "action": {"button": button_text, "sections": []},
            },
        }

        # Add header if provided
        if header_text:
            payload["interactive"]["header"] = {"type": "text", "text": header_text}

        # Prepare sections
        for section in sections:
            section_data = {"title": section["title"], "rows": []}

            for item in section["items"]:
                section_data["rows"].append(
                    {
                        "id": item["id"],
                        "title": item["title"],
                        "description": item.get("description", ""),
                    }
                )

            payload["interactive"]["action"]["sections"].append(section_data)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.url, headers=self.headers, json=payload
                )
                response_data = response.json()

                if response.status_code != 200:
                    self._handle_api_error(
                        response_data, phone_number, "interactive list"
                    )
                else:
                    self.logger.info(f"Sent interactive list to {phone_number}")

                return response_data
        except Exception as e:
            error_msg = f"Exception sending interactive list: {str(e)}"
            self.logger.error(error_msg)
            return {"error": {"message": error_msg, "type": "Exception"}}

    def _handle_api_error(
        self,
        response_data: Dict[str, Any],
        phone_number: str,
        content_type: str = "message",
    ) -> None:
        """Handle and log WhatsApp API errors."""

        error_info = response_data.get("error", {})
        error_code = error_info.get("code")
        error_message = error_info.get("message", "Unknown error")

        if error_code == 131030:
            # This is a common error in test environments when recipient isn't in the allowed list
            error_details = "Recipient phone number not in allowed list. Add the number to test numbers in Meta developer portal."
            self.logger.error(f"WhatsApp API Error {error_code}: {error_details}")
        else:
            self.logger.error(
                f"Failed to send {content_type} to {phone_number}: {error_message} (Code: {error_code})"
            )

        self.logger.warning(
            f"{content_type.capitalize()} not delivered to {phone_number} due to API error"
        )

    def _format_error_message(self, response_data: Dict[str, Any]) -> Dict[str, str]:
        """Format API error message for consistent error reporting."""

        error_info = response_data.get("error", {})
        error_code = error_info.get("code", "unknown")
        error_message = error_info.get("message", "Unknown error")

        return {"code": str(error_code), "message": error_message}
