import asyncio
from app.services.common.logging import setup_logger
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
        self.execution_handler = ExecutionHandler(self.whatsapp, self.state_manager)

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
                    await handler(client_id, message_text.strip().lower())
                else:
                    self.logger.warning(f"No handler found for state {current_state}")
                    await self.send_message(
                        client_id, "I'm not sure what to do next. Let's start over."
                    )
                    self.state_manager.set_state(client_id, WorkflowState.INIT)

            except Exception as e:
                self.logger.error(
                    f"Error processing message for {client_id} on state {current_state} at message {message_text}: {e}"
                )
                await self.send_message(
                    client_id,
                    "An error occurred while processing your message. Let's try again.",
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
