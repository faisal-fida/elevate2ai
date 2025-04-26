from app.services.common.logging import setup_logger
from app.services.messaging.client import WhatsApp
from app.services.messaging.state_manager import StateManager
from app.services.content.generator import ContentGenerator
from app.config import settings
from app.services.workflow.social_media import SocialMediaWorkflow


class WorkflowManager:
    """Manager for all workflows"""

    def __init__(self):
        self.logger = setup_logger(__name__)
        self.state_manager = StateManager()
        self.whatsapp = WhatsApp(settings.WHATSAPP_TOKEN, settings.WHATSAPP_PHONE_NUMBER_ID)
        self.content_generator = ContentGenerator()
        self.social_media_workflow = SocialMediaWorkflow(
            self.whatsapp, self.state_manager, self.content_generator
        )

    async def process_message(self, client_id: str, message: str) -> None:
        """Process an incoming message"""
        self.logger.info(f"Processing message from {client_id}: {message[:50]}...")
        await self.social_media_workflow.process_message(client_id, message)
