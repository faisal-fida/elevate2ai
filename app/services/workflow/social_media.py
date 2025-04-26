from app.services.messaging.client import MessagingClient
from app.services.messaging.state_manager import StateManager, WorkflowState
from app.services.content.generator import ContentGenerator
from app.services.workflow.base import BaseWorkflow
from app.services.workflow.handlers.content_type_selection import ContentTypeSelectionHandler
from app.services.workflow.handlers.platform_selection_for_content import (
    PlatformSelectionForContentHandler,
)
from app.services.workflow.handlers.caption import CaptionHandler
from app.services.workflow.handlers.scheduling import SchedulingHandler
from app.services.workflow.handlers.execution import ExecutionHandler


class SocialMediaWorkflow(BaseWorkflow):
    def __init__(
        self,
        client: MessagingClient,
        state_manager: StateManager,
        content_generator: ContentGenerator,
    ):
        super().__init__(client, state_manager)
        self.content_generator = content_generator
        self.content_type_selection_handler = ContentTypeSelectionHandler(client, state_manager)
        self.platform_selection_handler = PlatformSelectionForContentHandler(client, state_manager)
        self.caption_handler = CaptionHandler(client, state_manager, content_generator)
        self.scheduling_handler = SchedulingHandler(client, state_manager)
        self.execution_handler = ExecutionHandler(client, state_manager)

    async def _message_processor(self, client_id: str) -> None:
        """Process messages from the queue for a specific client."""
        queue = self._get_message_queue(client_id)
        while True:
            message = await queue.get()
            try:
                current_state = self.state_manager.get_state(client_id)
                handler = {
                    WorkflowState.INIT: self._handle_init,
                    WorkflowState.CONTENT_TYPE_SELECTION: self.content_type_selection_handler.handle,
                    WorkflowState.PLATFORM_SELECTION_FOR_CONTENT: self.platform_selection_handler.handle,
                    WorkflowState.CAPTION_INPUT: self.caption_handler.handle,
                    WorkflowState.SCHEDULE_SELECTION: self.scheduling_handler.handle,
                    WorkflowState.CONFIRMATION: self.execution_handler.handle_confirmation,
                    WorkflowState.POST_EXECUTION: self.execution_handler.handle,
                }.get(current_state)

                if handler:
                    await handler(client_id, message.strip().lower())
                else:
                    self.logger.warning(f"No handler found for state {current_state}")
                    await self.send_message(
                        client_id, "I'm not sure what to do next. Let's start over."
                    )
                    self.state_manager.set_state(client_id, WorkflowState.INIT)

            except Exception as e:
                self.logger.error(
                    f"Error processing message for {client_id} on state {current_state} at message {message}: {e}"
                )
                await self.send_message(
                    client_id, "An error occurred while processing your message. Let's try again."
                )
            finally:
                queue.task_done()

    async def _handle_init(self, client_id: str, message: str) -> None:
        """Handle the initial state"""
        if message in ["hi", "hello", "hey", "hii"]:
            # Start with content type selection
            self.state_manager.set_state(client_id, WorkflowState.CONTENT_TYPE_SELECTION)
            await self.content_type_selection_handler.send_content_type_options(client_id)
        else:
            await self.send_message(client_id, "To create a social media post, please type 'Hi'.")
