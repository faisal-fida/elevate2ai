from __future__ import annotations
import logging
import httpx
from typing import Dict, Any, List, Optional
from .base import WhatsAppBase

class TemplateHandler(WhatsAppBase):
    """Handles WhatsApp message templates and interactive components."""

    async def send_template(
        self, 
        template: str, 
        recipient_id: str, 
        components: List[Dict[str, Any]], 
        lang: str = "en_US",
        recipient_type: str = "individual"
    ) -> Dict[str, Any]:
        """Send a template message.

        Args:
            template: Template name
            recipient_id: Recipient's phone number without +
            components: List of template components
            lang: Template language code
            recipient_type: Either 'individual' or 'group'

        Returns:
            API response dictionary
        """
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": recipient_id,
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": lang},
                "components": components,
            },
        }
        logging.info(f"Sending template {template} to {recipient_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            logging.info(f"Template sent to {recipient_id}")
        else:
            logging.error(f"Failed to send template: {response.text}")
        return response.json()

    async def send_button(
        self, 
        recipient_id: str, 
        button_data: Dict[str, Any],
        recipient_type: str = "individual"
    ) -> Dict[str, Any]:
        """Send an interactive button message.

        Args:
            recipient_id: Recipient's phone number without +
            button_data: Button configuration data
            recipient_type: Either 'individual' or 'group'

        Returns:
            API response dictionary
        """
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": recipient_id,
            "type": "interactive",
            **button_data
        }
        logging.info(f"Sending button message to {recipient_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            logging.info(f"Button message sent to {recipient_id}")
        else:
            logging.error(f"Failed to send button message: {response.text}")
        return response.json()

    async def send_location(
        self, 
        lat: str, 
        long: str, 
        name: str, 
        address: str, 
        recipient_id: str,
        recipient_type: str = "individual"
    ) -> Dict[str, Any]:
        """Send a location message.

        Args:
            lat: Latitude coordinate
            long: Longitude coordinate
            name: Location name
            address: Location address
            recipient_id: Recipient's phone number without +
            recipient_type: Either 'individual' or 'group'

        Returns:
            API response dictionary
        """
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": recipient_id,
            "type": "location",
            "location": {
                "latitude": lat,
                "longitude": long,
                "name": name,
                "address": address,
            },
        }
        logging.info(f"Sending location to {recipient_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            logging.info(f"Location sent to {recipient_id}")
        else:
            logging.error(f"Failed to send location: {response.text}")
        return response.json()