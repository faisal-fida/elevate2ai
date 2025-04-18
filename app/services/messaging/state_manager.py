from enum import Enum
from typing import Dict

class WorkflowState(Enum):
    INIT = "init"
    WAITING_FOR_PROMO = "waiting_for_promo"
    WAITING_FOR_APPROVAL = "waiting_for_approval"

class StateManager:
    def __init__(self):
        self.client_states: Dict[str, WorkflowState] = {}
        self.client_contexts: Dict[str, dict] = {}

    def get_state(self, client_id: str) -> WorkflowState:
        """Get current state for a client."""
        return self.client_states.get(client_id, WorkflowState.INIT)

    def set_state(self, client_id: str, state: WorkflowState) -> None:
        """Set state for a client."""
        self.client_states[client_id] = state

    def get_context(self, client_id: str) -> dict:
        """Get context data for a client."""
        return self.client_contexts.get(client_id, {})

    def set_context(self, client_id: str, context: dict) -> None:
        """Set context data for a client."""
        self.client_contexts[client_id] = context

    def update_context(self, client_id: str, updates: dict) -> None:
        """Update context data for a client."""
        context = self.get_context(client_id)
        context.update(updates)
        self.set_context(client_id, context)

    def clear_context(self, client_id: str) -> None:
        """Clear context data for a client."""
        self.client_contexts.pop(client_id, None)

    def reset_client(self, client_id: str) -> None:
        """Reset both state and context for a client."""
        self.set_state(client_id, WorkflowState.INIT)
        self.clear_context(client_id)