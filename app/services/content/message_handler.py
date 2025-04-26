from __future__ import annotations
import logging
from app.services.messaging.whatsapp import WhatsApp
from app.services.messaging.state_manager import StateManager, WorkflowState
from .generator import ContentGenerator
from app.services.content.handlers import PromoHandler, SocialMediaHandler


class MessageHandler:
    """Main message handler that delegates to specific workflow handlers."""

    def __init__(
        self, whatsapp: WhatsApp, state_manager: StateManager, content_generator: ContentGenerator
    ):
        self.whatsapp = whatsapp
        self.state_manager = state_manager
        self.content_generator = content_generator
        self.logger = logging.getLogger(__name__)

        # Initialize handlers
        self.social_media_handler = SocialMediaHandler(whatsapp, state_manager)
        self.promo_handler = PromoHandler(
            whatsapp, state_manager, content_generator, self.social_media_handler
        )

        # Map states to handler methods
        self.handlers = {
            # Original workflow states
            WorkflowState.INIT: self.promo_handler.handle_init,
            WorkflowState.WAITING_FOR_PROMO: self.promo_handler.handle_promo_text,
            WorkflowState.WAITING_FOR_APPROVAL: self.promo_handler.handle_approval,
            # Social media posting workflow states
            WorkflowState.PLATFORM_SELECTION: self.social_media_handler.handle_platform_selection,
            WorkflowState.CONTENT_TYPE_SELECTION: self.social_media_handler.handle_content_type_selection,
            WorkflowState.SAME_CONTENT_CONFIRMATION: self.social_media_handler.handle_same_content_confirmation,
            WorkflowState.PLATFORM_SPECIFIC_CONTENT: self.social_media_handler.handle_platform_specific_content,
            WorkflowState.CAPTION_INPUT: self.social_media_handler.handle_caption_input,
            WorkflowState.SCHEDULE_SELECTION: self.social_media_handler.handle_schedule_selection,
            WorkflowState.CONFIRMATION: self.social_media_handler.handle_confirmation,
        }

    async def process_message(self, client_id: str, message: str) -> None:
        """Process a message from a client by delegating to the appropriate handler."""
        current_state = self.state_manager.get_state(client_id)
        handler = self.handlers.get(current_state)

        if handler:
            await handler(client_id, message.strip().lower())
        else:
            self.logger.warning(f"No handler found for state: {current_state}")
            # Default to init handler if no handler is found
            await self.promo_handler.handle_init(client_id, message.strip().lower())
