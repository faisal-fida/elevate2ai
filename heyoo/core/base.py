"""Base WhatsApp class with core functionality and configuration."""
from __future__ import annotations
import logging
from typing import Dict, Any, Optional

class WhatsAppBase:
    """Base WhatsApp class that handles authentication and API configuration."""

    def __init__(self, token: Optional[str] = None, phone_number_id: Optional[str] = None):
        """Initialize WhatsApp base configuration.

        Args:
            token (str): WhatsApp Cloud API token from developer portal
            phone_number_id (str): WhatsApp phone number ID from developer portal
        """
        self.token = token
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v14.0"
        self.v15_base_url = "https://graph.facebook.com/v15.0"
        self.url = f"{self.base_url}/{phone_number_id}/messages"
        self.headers = self._get_headers()
        
        # Configure logging
        logging.getLogger(__name__).addHandler(logging.NullHandler())

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests.

        Returns:
            Dict containing Content-Type and Authorization headers
        """
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

    def preprocess(self, data: Dict[Any, Any]) -> Dict[Any, Any]:
        """Preprocess webhook data before handling.

        Args:
            data: Raw webhook data

        Returns:
            Preprocessed data dictionary
        """
        if data.get("object"):
            if (
                "entry" in data
                and data["entry"]
                and data["entry"][0].get("changes")
                and data["entry"][0]["changes"][0].get("value")
            ):
                return data["entry"][0]["changes"][0]["value"]
        return data