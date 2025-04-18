from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel


class Message(BaseModel):
    """Base message model for all messaging platforms"""

    content: str
    recipient_id: str
    message_type: str = "text"
    context: Dict[str, Any] = {}


class MessagingClient(ABC):
    """Abstract base class for messaging clients"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.addHandler(logging.NullHandler())

    @abstractmethod
    async def send_message(self, message: Message) -> Dict[str, Any]:
        """Send a message to a recipient"""
        pass

    @abstractmethod
    def extract_message(self, data: Dict[Any, Any]) -> Optional[Message]:
        """Extract message from platform-specific webhook data"""
        pass


class WhatsAppBase(MessagingClient):
    def __init__(self, token: Optional[str] = None, phone_number_id: Optional[str] = None):
        super().__init__()
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
