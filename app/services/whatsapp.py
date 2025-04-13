from typing import Optional, Dict, Any, List
from heyoo import WhatsApp
import logging
from functools import wraps
from time import sleep
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_on_failure(max_retries=3, delay=1):
    """Decorator for retrying failed WhatsApp API calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Failed after {max_retries} retries: {str(e)}")
                        raise
                    logger.warning(f"Attempt {retries} failed, retrying in {delay} seconds...")
                    sleep(delay)
            return None
        return wrapper
    return decorator

class WhatsAppService:
    def __init__(self, token: str = None, phone_number_id: str = None):
        """Initialize WhatsApp service with credentials"""
        self.token = token or settings.WHATSAPP_TOKEN
        self.phone_number_id = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID
        self.messenger = WhatsApp(self.token, self.phone_number_id)
        logger.info("WhatsApp service initialized")

    @retry_on_failure()
    def send_message(self, to: str, message: str, preview_url: bool = False) -> Dict[str, Any]:
        """Send a text message to a WhatsApp number"""
        try:
            response = self.messenger.send_message(message, to, preview_url=preview_url)
            logger.info(f"Message sent successfully to {to}")
            return response
        except Exception as e:
            logger.error(f"Error sending message to {to}: {str(e)}")
            raise

    @retry_on_failure()
    def send_template(self, to: str, template: str, language: str, components: List[Dict] = None) -> Dict[str, Any]:
        """Send a template message"""
        try:
            response = self.messenger.send_template(template, to, language, components)
            logger.info(f"Template message '{template}' sent successfully to {to}")
            return response
        except Exception as e:
            logger.error(f"Error sending template message to {to}: {str(e)}")
            raise

    @retry_on_failure()
    def send_image(self, to: str, image: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """Send an image message"""
        try:
            response = self.messenger.send_image(image=image, recipient_id=to, caption=caption)
            logger.info(f"Image sent successfully to {to}")
            return response
        except Exception as e:
            logger.error(f"Error sending image to {to}: {str(e)}")
            raise

    @retry_on_failure()
    def send_document(self, to: str, document: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """Send a document"""
        try:
            response = self.messenger.send_document(document=document, recipient_id=to, caption=caption)
            logger.info(f"Document sent successfully to {to}")
            return response
        except Exception as e:
            logger.error(f"Error sending document to {to}: {str(e)}")
            raise

    @retry_on_failure()
    def send_audio(self, to: str, audio: str) -> Dict[str, Any]:
        """Send an audio message"""
        try:
            response = self.messenger.send_audio(audio=audio, recipient_id=to)
            logger.info(f"Audio sent successfully to {to}")
            return response
        except Exception as e:
            logger.error(f"Error sending audio to {to}: {str(e)}")
            raise

    @retry_on_failure()
    def send_video(self, to: str, video: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """Send a video message"""
        try:
            response = self.messenger.send_video(video=video, recipient_id=to, caption=caption)
            logger.info(f"Video sent successfully to {to}")
            return response
        except Exception as e:
            logger.error(f"Error sending video to {to}: {str(e)}")
            raise

    @retry_on_failure()
    def send_location(self, to: str, latitude: float, longitude: float, name: Optional[str] = None, address: Optional[str] = None) -> Dict[str, Any]:
        """Send a location"""
        try:
            response = self.messenger.send_location(lat=latitude, long=longitude, name=name, address=address, recipient_id=to)
            logger.info(f"Location sent successfully to {to}")
            return response
        except Exception as e:
            logger.error(f"Error sending location to {to}: {str(e)}")
            raise

    @retry_on_failure()
    def send_button(self, to: str, button_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a button message"""
        try:
            response = self.messenger.send_button(recipient_id=to, **button_data)
            logger.info(f"Button message sent successfully to {to}")
            return response
        except Exception as e:
            logger.error(f"Error sending button message to {to}: {str(e)}")
            raise

    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """Mark a message as read"""
        try:
            response = self.messenger.mark_as_read(message_id)
            logger.info(f"Message {message_id} marked as read")
            return response
        except Exception as e:
            logger.error(f"Error marking message {message_id} as read: {str(e)}")
            raise



if __name__ == "__main__":
    # Example usage
    whatsapp_service = WhatsAppService()
    response = whatsapp_service.send_message("+2348035080151", "Hello, this is a test message!")