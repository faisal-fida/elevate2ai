from typing import Protocol, Dict
from datetime import datetime
import asyncio
import logging
from abc import ABC, abstractmethod

class MessageSender(Protocol):
    async def send_message(self, phone_number: str, text: str) -> None:
        ...

    async def send_media(self, phone_number: str, media_url: str, caption: str) -> None:
        ...

class BaseMessageHandler(ABC):
    def __init__(self):
        self.last_message_time: Dict[str, datetime] = {}
        self.rate_limit_delay = 1.0  # Seconds between messages

    async def _check_rate_limit(self, phone_number: str) -> None:
        """Enforce rate limiting for messages."""
        now = datetime.now()
        if phone_number in self.last_message_time:
            time_since_last = (now - self.last_message_time[phone_number]).total_seconds()
            if time_since_last < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
    async def _update_rate_limit(self, phone_number: str) -> None:
        """Update the last message time for rate limiting."""
        self.last_message_time[phone_number] = datetime.now()

    async def _handle_message_operation(self, phone_number: str, operation: str, **kwargs) -> None:
        """Generic message operation handler with rate limiting and error handling."""
        try:
            await self._check_rate_limit(phone_number)
            await self._execute_operation(operation, phone_number, **kwargs)
            await self._update_rate_limit(phone_number)
        except Exception as e:
            logging.error(f"Error in {operation} for {phone_number}: {e}")
            raise

    @abstractmethod
    async def _execute_operation(self, operation: str, phone_number: str, **kwargs) -> None:
        """Execute the specific message operation."""
        pass

class MessageHandler(BaseMessageHandler):
    def __init__(self, sender: MessageSender):
        super().__init__()
        self.sender = sender

    async def _execute_operation(self, operation: str, phone_number: str, **kwargs) -> None:
        """Execute specific message operations."""
        if operation == 'send_message':
            await self.sender.send_message(phone_number=phone_number, text=kwargs.get('text', ''))
        elif operation == 'send_media':
            await self.sender.send_media(
                phone_number=phone_number,
                media_url=kwargs.get('media_url', ''),
                caption=kwargs.get('caption', '')
            )

    async def send_message(self, phone_number: str, text: str) -> None:
        """Send a text message with rate limiting."""
        await self._handle_message_operation(phone_number, 'send_message', text=text)

    async def send_media(self, phone_number: str, media_url: str, caption: str) -> None:
        """Send a media message with rate limiting."""
        await self._handle_message_operation(
            phone_number,
            'send_media',
            media_url=media_url,
            caption=caption
        )