from enum import Enum
from typing import Dict, Any
from app.services.common.logging import setup_logger
from app.services.common.types import WorkflowStateType


class WorkflowState(Enum):
    """Enum for workflow states"""

    INIT = "init"
    WAITING_FOR_PROMO = "waiting_for_promo"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    CONTENT_TYPE_SELECTION = "content_type_selection"
    PLATFORM_SELECTION_FOR_CONTENT = "platform_selection_for_content"
    CAPTION_INPUT = "caption_input"
    SCHEDULE_SELECTION = "schedule_selection"
    CONFIRMATION = "confirmation"
    IMAGE_INCLUSION_DECISION = "image_inclusion_decision"
    POST_EXECUTION = "post_execution"

    # New states for template-specific input collection
    WAITING_FOR_DESTINATION = "waiting_for_destination"
    WAITING_FOR_EVENT_NAME = "waiting_for_event_name"
    WAITING_FOR_PRICE = "waiting_for_price"

    # Media selection states
    MEDIA_SOURCE_SELECTION = "media_source_selection"
    WAITING_FOR_MEDIA_UPLOAD = "waiting_for_media_upload"
    VIDEO_SELECTION = "video_selection"


class StateManager:
    """Manages workflow states for clients"""

    def __init__(self):
        self.client_states: Dict[str, WorkflowState] = {}
        self.client_contexts: Dict[str, Dict[str, Any]] = {}
        self.logger = setup_logger(__name__)

    def get_state(self, client_id: str) -> WorkflowState:
        """Get current state for a client."""
        if client_id not in self.client_states:
            self.logger.info(f"No state found for {client_id}, setting to INIT")
            self.client_states[client_id] = WorkflowState.INIT
        return self.client_states.get(client_id, WorkflowState.INIT)

    def set_state(self, client_id: str, state: WorkflowState) -> None:
        """Set state for a client."""
        # log non-empty contexts for single client
        non_empty_context = {
            key: value for key, value in self.get_context(client_id).items() if value
        }
        if non_empty_context:
            self.logger.warning(
                f"State is {state.name} and Context for {client_id} is {non_empty_context}"
            )
        self.client_states[client_id] = state

    def get_context(self, client_id: str) -> Dict[str, Any]:
        """Get context data for a client."""
        if client_id not in self.client_contexts:
            self.client_contexts[client_id] = {}
        return self.client_contexts.get(client_id, {})

    def set_context(self, client_id: str, context: Dict[str, Any]) -> None:
        """Set context data for a client."""
        self.client_contexts[client_id] = context

    def update_context(self, client_id: str, updates: Dict[str, Any]) -> None:
        """Update context data for a client."""
        context = self.get_context(client_id)

        # Handle Pydantic models by converting to dict if needed
        if hasattr(updates, "model_dump"):
            updates = updates.model_dump()

        context.update(updates)
        self.set_context(client_id, context)

    def clear_context(self, client_id: str) -> None:
        """Clear context data for a client."""
        self.client_contexts.pop(client_id, None)

    def reset_client(self, client_id: str) -> None:
        """Reset both state and context for a client."""
        self.set_state(client_id, WorkflowState.INIT)
        self.clear_context(client_id)

    def get_state_name(self, client_id: str) -> WorkflowStateType:
        """Get the state name for a client"""
        state = self.get_state(client_id)
        return state.value
