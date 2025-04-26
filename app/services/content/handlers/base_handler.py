from __future__ import annotations
import logging
from typing import Type
from app.services.messaging.whatsapp import WhatsApp
from app.services.messaging.state_manager import StateManager, WorkflowState
from app.services.content.contexts.base_context import BaseWorkflowContext


class BaseHandler:
    """Base class for all workflow handlers."""

    def __init__(
        self,
        whatsapp: WhatsApp,
        state_manager: StateManager,
        context_class: Type[BaseWorkflowContext] = BaseWorkflowContext,
    ):
        self.whatsapp = whatsapp
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)
        self.context_class = context_class

    async def _send_message(self, client_id: str, message: str) -> None:
        """Send a text message to the client."""
        await self.whatsapp.send_message(phone_number=client_id, message=message)

    def get_context(self, client_id: str) -> BaseWorkflowContext:
        """Get the workflow context for a client."""
        context_dict = self.state_manager.get_context(client_id)
        return self.context_class(**context_dict) if context_dict else self.context_class()

    def update_context(self, client_id: str, context: BaseWorkflowContext) -> None:
        """Update the workflow context for a client."""
        self.state_manager.update_context(client_id, vars(context))

    def set_state(self, client_id: str, state: WorkflowState) -> None:
        """Set the workflow state for a client."""
        self.state_manager.set_state(client_id, state)

    async def handle_message(self, client_id: str, message: str) -> None:
        """Handle a message from the client. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement handle_message")
