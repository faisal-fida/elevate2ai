from enum import Enum, auto
from typing import Dict, Any
import json

from app.services.common.logging import setup_logger
from app.services.common.types import WorkflowStateType


class WorkflowState(Enum):
    INIT = auto()
    CONTENT_TYPE_SELECTION = auto()
    PLATFORM_SELECTION = auto()
    PLATFORM_SELECTION_FOR_CONTENT = auto()
    CAPTION_INPUT = auto()
    CAPTION_GENERATION = auto()
    MEDIA_SOURCE_SELECTION = auto()
    WAITING_FOR_MEDIA_UPLOAD = auto()
    VIDEO_SELECTION = auto()
    SCHEDULE_SELECTION = auto()
    CONFIRMATION = auto()
    POST_EXECUTION = auto()
    WAITING_FOR_DESTINATION = auto()
    WAITING_FOR_EVENT_NAME = auto()
    WAITING_FOR_PRICE = auto()
    WAITING_FOR_HEADLINE = auto()
    IMAGE_INCLUSION_DECISION = auto()
    IMAGE_SELECTION = auto()  # New state for selecting from multiple images


class StateManager:
    def __init__(self):
        self.logger = setup_logger(__name__)
        self._state_store: Dict[str, WorkflowState] = {}
        self._context_store: Dict[str, Dict[str, Any]] = {}

    def get_state(self, client_id: str) -> WorkflowState:
        """
        Get the current state for a client.

        If no state exists, initializes to INIT state.

        Args:
            client_id: The client identifier

        Returns:
            The current workflow state for the client
        """
        if client_id not in self._state_store:
            self._state_store[client_id] = WorkflowState.INIT
            self.logger.info(
                f"Initialized state for {client_id} to {WorkflowState.INIT.name}"
            )

        return self._state_store[client_id]

    def set_state(self, client_id: str, state: WorkflowState) -> None:
        """
        Set the state for a client.

        Args:
            client_id: The client identifier
            state: The new workflow state
        """
        prev_state = (
            self.get_state(client_id).name if client_id in self._state_store else "None"
        )
        self._state_store[client_id] = state
        self.logger.info(
            f"State transition for {client_id}: {prev_state} -> {state.name}"
        )

    def get_context(self, client_id: str) -> Dict[str, Any]:
        """
        Get the context for a client.

        If no context exists, initializes to an empty dictionary.

        Args:
            client_id: The client identifier

        Returns:
            The context dictionary for the client
        """
        if client_id not in self._context_store:
            self._context_store[client_id] = {}

        return self._context_store[client_id]

    def update_context(self, client_id: str, context: Dict[str, Any]) -> None:
        """
        Update the context for a client.

        Args:
            client_id: The client identifier
            context: The new context dictionary
        """
        self._context_store[client_id] = context

        # Log a shortened version of the context for debugging
        try:
            context_str = json.dumps(context, default=str)
            if len(context_str) > 200:
                context_preview = context_str[:200] + "..."
            else:
                context_preview = context_str

            self.logger.debug(f"Updated context for {client_id}: {context_preview}")
        except Exception as e:
            self.logger.error(f"Error logging context: {e}")

    def reset_client(self, client_id: str) -> None:
        """
        Reset state and context for a client.

        Args:
            client_id: The client identifier
        """
        self._state_store[client_id] = WorkflowState.INIT
        self._context_store[client_id] = {}
        self.logger.info(f"Reset state and context for {client_id}")

    def get_context_value(self, client_id: str, key: str, default: Any = None) -> Any:
        """
        Get a specific value from a client's context.

        Args:
            client_id: The client identifier
            key: The context key to retrieve
            default: Default value if key not found

        Returns:
            The value for the specified key or the default value
        """
        context = self.get_context(client_id)
        return context.get(key, default)

    def set_context_value(self, client_id: str, key: str, value: Any) -> None:
        """
        Set a specific value in a client's context.

        Args:
            client_id: The client identifier
            key: The context key to set
            value: The value to set
        """
        context = self.get_context(client_id)
        context[key] = value
        self.update_context(client_id, context)
        self.logger.debug(f"Set context value for {client_id}: {key} = {value}")

    def get_state_name(self, client_id: str) -> WorkflowStateType:
        """Get the state name for a client"""
        state = self.get_state(client_id)
        return state.value
