import asyncio
from app.services.common.logging import setup_logger, log_exception
from app.services.common.debug import dump_context, save_error_snapshot
from app.services.messaging.client import WhatsApp
from app.config import settings
from app.services.messaging.state_manager import StateManager, WorkflowState
from app.services.content.generator import ContentGenerator
from app.services.workflow.handlers.content_type_selection import (
    ContentTypeSelectionHandler,
)
from app.services.workflow.handlers.platform_selection_for_content import (
    PlatformSelectionForContentHandler,
)
from app.services.workflow.handlers.caption import CaptionHandler
from app.services.workflow.handlers.scheduling import SchedulingHandler
from app.services.workflow.handlers.execution import ExecutionHandler


class WorkflowManager:
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.state_manager = StateManager()
        self.whatsapp = WhatsApp(
            settings.WHATSAPP_TOKEN, settings.WHATSAPP_PHONE_NUMBER_ID
        )
        self.content_generator = ContentGenerator()
        self.client_queues = {}
        self.client_processing_tasks = {}

        self.content_type_selection_handler = ContentTypeSelectionHandler(
            self.whatsapp, self.state_manager
        )
        self.platform_selection_handler = PlatformSelectionForContentHandler(
            self.whatsapp, self.state_manager
        )
        self.caption_handler = CaptionHandler(
            self.whatsapp, self.state_manager, self.content_generator
        )
        self.scheduling_handler = SchedulingHandler(self.whatsapp, self.state_manager)
        self.execution_handler = ExecutionHandler(
            self.whatsapp, self.state_manager, self.scheduling_handler
        )

    async def process_message(self, client_id: str, message: str) -> None:
        """Add an incoming message to the client's queue and ensure the processor is running."""
        self.logger.info(f"Queueing message from {client_id}: {message[:50]}...")
        queue = self._get_message_queue(client_id)
        await queue.put(message)

        if (
            client_id not in self.client_processing_tasks
            or self.client_processing_tasks[client_id].done()
        ):
            self.logger.info(f"Starting message processor for client {client_id}")
            task = asyncio.create_task(self._message_processor(client_id))
            self.client_processing_tasks[client_id] = task
        else:
            self.logger.info(
                f"Message processor already running for client {client_id}"
            )

    async def _message_processor(self, client_id: str) -> None:
        """Process messages from the queue for a specific client."""
        queue = self._get_message_queue(client_id)
        while True:
            message_text = await queue.get()  # Renamed variable for clarity
            current_state = None
            try:
                current_state = self.state_manager.get_state(client_id)
                self.logger.info(
                    f"Processing message in state {current_state.name} for {client_id}: {message_text[:20]}..."
                )

                # Map states to their handlers
                handler_map = {
                    WorkflowState.INIT: self._handle_init,
                    WorkflowState.CONTENT_TYPE_SELECTION: self.content_type_selection_handler.handle,
                    WorkflowState.PLATFORM_SELECTION_FOR_CONTENT: self.platform_selection_handler.handle,
                    WorkflowState.CAPTION_INPUT: self.caption_handler.handle,
                    WorkflowState.SCHEDULE_SELECTION: self.scheduling_handler.handle,
                    WorkflowState.CONFIRMATION: self.execution_handler.handle_confirmation,
                    WorkflowState.IMAGE_INCLUSION_DECISION: self.execution_handler.handle,
                    WorkflowState.POST_EXECUTION: self.execution_handler.handle,
                    # New template-specific input states
                    WorkflowState.WAITING_FOR_DESTINATION: self.caption_handler.handle,
                    WorkflowState.WAITING_FOR_EVENT_NAME: self.caption_handler.handle,
                    WorkflowState.WAITING_FOR_PRICE: self.caption_handler.handle,
                    WorkflowState.WAITING_FOR_EVENT_IMAGE: self.caption_handler.handle,
                    # Media selection states
                    WorkflowState.MEDIA_SOURCE_SELECTION: self.caption_handler.handle,
                    WorkflowState.WAITING_FOR_MEDIA_UPLOAD: self.caption_handler.handle,
                    WorkflowState.VIDEO_SELECTION: self.caption_handler.handle,
                }

                # Get the appropriate handler for the current state
                handler = handler_map.get(current_state)

                if handler:
                    # Dump context before processing for debugging purposes
                    context = self.state_manager.get_context(client_id)
                    dump_context(client_id, context, f"before_{current_state.name}")

                    # Process the message
                    await handler(client_id, message_text.strip().lower())

                    # Dump context after processing to track changes
                    updated_context = self.state_manager.get_context(client_id)
                    dump_context(
                        client_id, updated_context, f"after_{current_state.name}"
                    )
                else:
                    error_msg = f"No handler found for state {current_state.name}"
                    self.logger.warning(error_msg)

                    # Log detailed context information for debugging
                    context = self.state_manager.get_context(client_id)
                    self.logger.warning(f"Client context: {context}")

                    # Dump context for debugging
                    dump_context(
                        client_id, context, f"error_no_handler_{current_state.name}"
                    )

                    await self.send_message(
                        client_id,
                        f"I'm not sure what to do next. Let's start over. (Error ID: state_{current_state.name})",
                    )
                    self.state_manager.set_state(client_id, WorkflowState.INIT)

            except Exception as e:
                # Use our enhanced exception logging with full context
                state_name = current_state.name if current_state else "UNKNOWN"

                # Get current context data
                context = self.state_manager.get_context(client_id)

                # Save detailed error snapshot with context
                error_id = save_error_snapshot(
                    error=e, client_id=client_id, state=state_name, context=context
                )

                error_msg = (
                    f"Error processing message for {client_id}\n"
                    f"State: {state_name}\n"
                    f"Message: '{message_text}'\n"
                    f"Error ID: {error_id}"
                )

                # Log exception with full traceback
                log_exception(self.logger, error_msg, e)

                # Send user-friendly message with error ID for support reference
                await self.send_message(
                    client_id,
                    f"An error occurred while processing your message. Please try again or contact support with error ID: {error_id}",
                )
            finally:
                queue.task_done()

    async def _handle_init(
        self, client_id: str, message_text: str
    ) -> None:  # Renamed variable
        """Handle the initial state"""
        if message_text in ["hi", "hello", "hey", "hii"]:
            # Start with content type selection
            self.state_manager.set_state(
                client_id, WorkflowState.CONTENT_TYPE_SELECTION
            )
            await self.content_type_selection_handler.send_content_type_options(
                client_id
            )
        else:
            await self.send_message(
                client_id, "To create a social media post, please type 'Hi'."
            )

    def _get_message_queue(self, client_id: str) -> asyncio.Queue:
        """Retrieve or create the message queue for a specific client."""
        if client_id not in self.client_queues:
            self.logger.info(f"Creating new message queue for client {client_id}")
            self.client_queues[client_id] = asyncio.Queue()
        return self.client_queues[client_id]

    async def send_message(self, client_id: str, message: str) -> None:
        """Send a message to the client"""
        await self.whatsapp.send_message(client_id, message)
