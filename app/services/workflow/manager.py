import asyncio
from app.logging import setup_logger, log_exception
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
from app.services.messaging.media_utils import save_whatsapp_image


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

    async def process_message(
        self,
        client_id: str,
        message: str,
        message_type: str = "text",
        is_media_message: bool = False,
    ) -> None:
        """Add an incoming message to the client's queue and ensure the processor is running."""
        context = self.state_manager.get_context(client_id)
        context["current_message_type"] = message_type
        context["is_media_message"] = is_media_message

        if is_media_message and message.startswith("MEDIA_MESSAGE:"):
            parts = message.split(":")
            if len(parts) >= 3:
                media_type = parts[1]
                media_id = parts[2]
                self.logger.info(f"Processing {media_type} message with ID: {media_id}")

        self.state_manager.update_context(client_id, context)

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
            self.logger.debug(
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
                    WorkflowState.WAITING_FOR_HEADLINE: self.caption_handler.handle,
                    WorkflowState.WAITING_FOR_PRICE: self.caption_handler.handle,
                    WorkflowState.WAITING_FOR_TIP_DETAILS: self.caption_handler.handle,
                    WorkflowState.WAITING_FOR_SEASONAL_DETAILS: self.caption_handler.handle,
                    # Media selection states
                    WorkflowState.MEDIA_SOURCE_SELECTION: self.caption_handler.handle,
                    WorkflowState.WAITING_FOR_MEDIA_UPLOAD: self.caption_handler.handle,
                    WorkflowState.VIDEO_SELECTION: self.caption_handler.handle,
                    WorkflowState.IMAGE_SELECTION: self.caption_handler.handle,
                    WorkflowState.WAITING_FOR_CAPTION: self.caption_handler.handle,
                }

                if message_text.startswith("MEDIA_MESSAGE:"):
                    parts = message_text.split(":")
                    if len(parts) >= 3:
                        media_type = parts[1]
                        media_id = parts[2]

                        context = self.state_manager.get_context(client_id)
                        if current_state == WorkflowState.WAITING_FOR_MEDIA_UPLOAD:
                            media_url = await save_whatsapp_image(media_id, client_id)

                            if media_url:
                                context["media_url"] = media_url
                                self.state_manager.update_context(client_id, context)

                                # Store the URL but preserve the original message format
                                # We'll keep the original message_text to maintain the structured format
                                # The handler will check context["media_url"] first
                                self.logger.info(
                                    f"Successfully retrieved {media_type} URL: {media_url[:50]}..."
                                )
                            else:
                                await self.send_message(
                                    client_id,
                                    f"I couldn't process your {media_type}. Please try uploading it again.",
                                )
                                queue.task_done()
                                continue

                handler = handler_map.get(current_state)

                if handler:
                    context = self.state_manager.get_context(client_id)

                    if message_text.startswith(
                        "MEDIA_MESSAGE:"
                    ) or message_text.startswith("/media/"):
                        await handler(client_id, message_text.strip())
                    else:
                        await handler(client_id, message_text.strip().lower())
                else:
                    error_msg = f"No handler found for state {current_state.name}"
                    self.logger.warning(error_msg)

                    context = self.state_manager.get_context(client_id)
                    self.logger.warning(f"Client context: {context}")

                    await self.send_message(
                        client_id,
                        f"I'm not sure what to do next. Let's start over. (Error ID: state_{current_state.name})",
                    )
                    self.state_manager.set_state(client_id, WorkflowState.INIT)

            except Exception as e:
                state_name = current_state.name if current_state else "UNKNOWN"
                context = self.state_manager.get_context(client_id)
                error_msg = (
                    f"Error processing message for {client_id}\n"
                    f"State: {state_name}\n"
                    f"Message: '{message_text}'\n"
                )
                log_exception(self.logger, error_msg, e)
                await self.send_message(
                    client_id,
                    "An error occurred while processing your request. Please try again.",
                )
                self.state_manager.set_state(client_id, WorkflowState.INIT)
            finally:
                queue.task_done()

    async def _handle_init(
        self, client_id: str, message_text: str
    ) -> None:  # Renamed variable
        """Handle the initial state"""
        if message_text in ["hi", "hello", "hey", "hii"]:
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
        await self.whatsapp.send_message(message, client_id)
