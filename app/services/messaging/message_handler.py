from typing import Protocol, Dict
from datetime import datetime
import asyncio
import logging

class MessageSender(Protocol):
    async def send_message(self, phone_number: str, text: str) -> None:
        ...

    async def send_media(self, phone_number: str, media_url: str, caption: str) -> None:
        ...

class MessageHandler:
    def __init__(self, sender: MessageSender):
        self.sender = sender
        self.last_message_time: Dict[str, datetime] = {}
        self.rate_limit_delay = 1.0  # Seconds between messages

    async def _check_rate_limit(self, phone_number: str) -> None:
        """Enforce rate limiting for messages."""
        now = datetime.now()
        if phone_number in self.last_message_time:
            time_since_last = (now - self.last_message_time[phone_number]).total_seconds()
            if time_since_last < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - time_since_last)

    async def send_message(self, phone_number: str, text: str) -> None:
        """Send a text message with rate limiting."""
        try:
            await self._check_rate_limit(phone_number)
            await self.sender.send_message(phone_number=phone_number, text=text)
            self.last_message_time[phone_number] = datetime.now()
        except Exception as e:
            logging.error(f"Error sending message to {phone_number}: {e}")
            raise

    async def send_media(self, phone_number: str, media_url: str, caption: str) -> None:
        """Send a media message with rate limiting."""
        try:
            await self._check_rate_limit(phone_number)
            await self.sender.send_media(
                phone_number=phone_number,
                media_url=media_url,
                caption=caption
            )
            self.last_message_time[phone_number] = datetime.now()
        except Exception as e:
            logging.error(f"Error sending media to {phone_number}: {e}")
            raise