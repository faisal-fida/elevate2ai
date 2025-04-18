from __future__ import annotations
import logging
from typing import Dict, Any, Optional

class WhatsAppBase:
    def __init__(self, token: Optional[str] = None, phone_number_id: Optional[str] = None):
        self.token = token
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v14.0"
        self.v15_base_url = "https://graph.facebook.com/v15.0"
        self.url = f"{self.base_url}/{phone_number_id}/messages"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
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