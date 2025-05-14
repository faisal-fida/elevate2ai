from typing import List
from app.services.messaging.client import MessagingClient
from app.services.messaging.state_manager import StateManager, WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.services.content.generator import ContentGenerator
from app.constants import MESSAGES, TEMPLATE_CONFIG
from app.services.common.types import WorkflowContext, MediaItem
from app.services.messaging.media_utils import save_whatsapp_image, cleanup_client_media


class CaptionHandler(BaseHandler):
    """Handler for caption input state"""

    def __init__(
        self,
        client: MessagingClient,
        state_manager: StateManager,
        content_generator: ContentGenerator,
    ):
        super().__init__(client, state_manager)
        self.content_generator = content_generator

    async def handle(self, client_id: str, message: str) -> None:
        """Handle caption input"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if we're waiting for image upload
        current_state = self.state_manager.get_state(client_id)
        if current_state == WorkflowState.WAITING_FOR_MEDIA_UPLOAD:
            await self.handle_media_upload(client_id, message)
            return

        # Handle template-specific input states
        if current_state == WorkflowState.WAITING_FOR_DESTINATION:
            await self.handle_destination_input(client_id, message)
            return
        elif current_state == WorkflowState.WAITING_FOR_EVENT_NAME:
            await self.handle_event_name_input(client_id, message)
            return
        elif current_state == WorkflowState.WAITING_FOR_PRICE:
            await self.handle_price_input(client_id, message)
            return

        if not message:
            await self.send_message(client_id, "Please enter a caption for your post.")
            return

        # Store the caption
        context.caption = message
        context.original_text = message
        self.state_manager.update_context(client_id, context.model_dump())

        # Find appropriate template
        if not context.template_id:
            for platform in context.selected_platforms:
                template_id = self.content_generator.get_template_by_platform_and_type(
                    platform=platform,
                    content_type=context.selected_content_type,
                    client_id=client_id,
                )
                if template_id:
                    context.template_id = template_id
                    context.template_type = context.selected_content_type

                    # Check template requirements
                    template = TEMPLATE_CONFIG["templates"].get(template_id, {})
                    required_keys = template.get("required_keys", [])

                    # If we already have a selected_image and template needs event_image, set it
                    if (
                        "event_image" in required_keys
                        and context.selected_image
                        and not context.event_image
                    ):
                        context.event_image = context.selected_image
                        self.logger.info(
                            "Setting event_image to selected_image for template compatibility"
                        )

                    self.state_manager.update_context(client_id, context.model_dump())
                    break

        # Check if we need to collect template-specific fields first
        if await self.request_template_fields(client_id):
            return  # Waiting for additional input

        # Generate content based on the caption
        await self.send_message(client_id, MESSAGES["generating"])

        try:
            if not context.template_id:
                # Fallback to regular content generation
                caption, image_urls = await self.content_generator.generate_content(
                    message
                )
                context.caption = caption
                context.image_urls = image_urls
            else:
                # Prepare user inputs for template
                user_inputs = {
                    "caption_text": message,
                }

                # Add template-specific fields
                if context.destination_name:
                    user_inputs["destination_name"] = context.destination_name
                if context.event_name:
                    user_inputs["event_name"] = context.event_name
                if context.price_text:
                    user_inputs["price_text"] = context.price_text
                if context.event_image:
                    user_inputs["event_image"] = context.event_image
                elif context.selected_image:
                    # If template needs event_image and we have selected_image, use it
                    template = TEMPLATE_CONFIG["templates"].get(context.template_id, {})
                    required_keys = template.get("required_keys", [])
                    if "event_image" in required_keys:
                        user_inputs["event_image"] = context.selected_image
                        context.event_image = context.selected_image
                        self.logger.info(
                            "Using selected_image as event_image for template"
                        )

                # Generate content using template
                (
                    caption,
                    media_urls,
                    template_data,
                ) = await self.content_generator.generate_template_content(
                    template_id=context.template_id, user_inputs=user_inputs
                )

                context.caption = caption
                context.image_urls = media_urls
                if media_urls:
                    context.selected_image = media_urls[0]
                context.template_data = template_data

        except ValueError as ve:
            # Handle validation errors
            self.logger.error(f"Validation error: {ve}")
            await self.send_message(client_id, f"Error generating content: {ve}")
            return

        except Exception as e:
            # Handle other errors
            self.logger.error(f"Error generating content: {e}")
            caption, image_urls = await self.content_generator.generate_content(message)
            context.caption = caption
            context.image_urls = image_urls

        # Send the generated caption
        await self.send_message(
            client_id, f"Here is the caption for the post: {context.caption}"
        )

        # Ask for image upload
        await self.ask_for_image_upload(client_id)

    async def request_template_fields(self, client_id: str) -> bool:
        """
        Request any template-specific fields that are required.
        Returns True if waiting for additional input.
        """
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Find template if not already set
        if not context.template_id:
            for platform in context.selected_platforms:
                template_id = self.content_generator.get_template_by_platform_and_type(
                    platform=platform,
                    content_type=context.selected_content_type,
                    client_id=client_id,
                )
                if template_id:
                    context.template_id = template_id
                    context.template_type = context.selected_content_type
                    break

        if not context.template_id:
            return False  # No template found, no additional fields needed

        # Get template details
        template = TEMPLATE_CONFIG["templates"].get(context.template_id, {})
        required_keys = template.get("required_keys", [])

        # If event_image is required and we have selected_image, use that
        if (
            "event_image" in required_keys
            and not context.event_image
            and context.selected_image
        ):
            context.event_image = context.selected_image
            self.logger.info(
                "Using selected_image as event_image for template compatibility"
            )
            self.state_manager.update_context(client_id, context.model_dump())

        # Check for required fields in order of priority
        if "destination_name" in required_keys and not context.destination_name:
            self.state_manager.set_state(
                client_id, WorkflowState.WAITING_FOR_DESTINATION
            )
            await self.send_message(
                client_id, "Please enter the destination name (5 words or less):"
            )
            return True

        if "event_name" in required_keys and not context.event_name:
            self.state_manager.set_state(
                client_id, WorkflowState.WAITING_FOR_EVENT_NAME
            )
            await self.send_message(
                client_id, "Please enter the event name (5 words or less):"
            )
            return True

        if "price_text" in required_keys and not context.price_text:
            self.state_manager.set_state(client_id, WorkflowState.WAITING_FOR_PRICE)
            await self.send_message(
                client_id,
                "Please enter the price or promotion details (e.g., '$99', '50% off'):",
            )
            return True

        # Only ask for event_image if we don't already have it from selected_image
        if "event_image" in required_keys and not context.event_image:
            # We'll need to ask for an image upload
            await self.send_message(client_id, "Please upload an image for your event:")
            self.state_manager.set_state(
                client_id, WorkflowState.WAITING_FOR_MEDIA_UPLOAD
            )
            return True

        return False  # No additional inputs needed

    async def handle_destination_input(self, client_id: str, message: str) -> None:
        """Handle destination name input"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if this is a document message
        if "received document with id:" in message.lower():
            # This is a document message, not a destination name
            await self.send_message(
                client_id,
                "I need a text name for your destination, not a document. Please enter the destination name (5 words or less):",
            )
            return

        # Validate the destination name
        is_valid, result = self.content_generator.openai_service.validate_user_input(
            message, max_words=5
        )

        if not is_valid:
            await self.send_message(client_id, result)
            return

        context.destination_name = result
        self.state_manager.update_context(client_id, context.model_dump())

        await self.send_message(client_id, f"Great! Destination name '{result}' saved.")

        # Return to caption input state and continue processing
        self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
        await self.handle(client_id, context.original_text)

    async def handle_event_name_input(self, client_id: str, message: str) -> None:
        """Handle event name input"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if this is a document message
        if "received document with id:" in message.lower():
            # This is a document message, not an event name
            await self.send_message(
                client_id,
                "I need a text name for your event, not a document. Please enter the event name (5 words or less):",
            )
            return

        # Validate the event name
        is_valid, result = self.content_generator.openai_service.validate_user_input(
            message, max_words=5
        )

        if not is_valid:
            await self.send_message(client_id, result)
            return

        context.event_name = result
        self.state_manager.update_context(client_id, context.model_dump())

        await self.send_message(client_id, f"Great! Event name '{result}' saved.")

        # Return to caption input state and continue processing
        self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
        await self.handle(client_id, context.original_text)

    async def handle_price_input(self, client_id: str, message: str) -> None:
        """Handle price input"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if this is a document message
        if "received document with id:" in message.lower():
            # This is a document message, not a price
            await self.send_message(
                client_id,
                "I need text for your price information, not a document. Please enter the price or promotion details (e.g., '$99', '50% off'):",
            )
            return

        # Store the price text
        context.price_text = message
        self.state_manager.update_context(client_id, context.model_dump())

        await self.send_message(
            client_id, f"Great! Price information '{message}' saved."
        )

        # Return to caption input state and continue processing
        self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
        await self.handle(client_id, context.original_text)

    async def ask_for_image_upload(self, client_id: str) -> None:
        """Ask the user to upload an image"""
        self.state_manager.set_state(client_id, WorkflowState.WAITING_FOR_MEDIA_UPLOAD)
        await self.send_message(client_id, "Please upload an image for your post.")

    async def handle_media_upload(self, client_id: str, message: str) -> None:
        """Handle image upload from WhatsApp"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Extract media ID from message
        if message.startswith("Received image with ID:") or message.startswith(
            "Received media with ID:"
        ):
            # Extract media ID from the message
            media_id = message.split("ID:")[-1].strip()
            self.logger.info(f"Processing image upload with ID: {media_id}")

            # Download and get public URL in one step
            public_url = await save_whatsapp_image(media_id, client_id)

            if public_url:
                # Store the public URL in the context
                context.selected_image = public_url

                # Also set event_image if needed by template
                if context.template_id:
                    template = TEMPLATE_CONFIG["templates"].get(context.template_id, {})
                    required_keys = template.get("required_keys", [])
                    if "event_image" in required_keys:
                        context.event_image = public_url
                        self.logger.info(
                            "Also setting event_image to the same URL for template compatibility"
                        )

                        # Update template data if it exists
                        if context.template_data:
                            context.template_data["event_image"] = public_url

                self.state_manager.update_context(client_id, context.model_dump())
                await self.send_message(client_id, "Image uploaded successfully!")

                # Move to scheduling
                self.state_manager.set_state(
                    client_id, WorkflowState.SCHEDULE_SELECTION
                )
                await self.send_scheduling_options(client_id)
            else:
                # Failed to download media
                await self.send_message(
                    client_id, "I couldn't process your image. Please upload it again."
                )
        elif message.startswith("http") and ("://" in message):
            # For direct URLs, just store the URL (we don't support this anymore)
            await self.send_message(
                client_id,
                "Please upload an image directly through WhatsApp instead of sending a URL.",
            )
        else:
            # Invalid format
            await self.send_message(
                client_id,
                "Please send your image as an attachment.",
            )

    async def complete_workflow(self, client_id: str) -> None:
        """Complete the workflow and clean up resources"""
        # Clean up media files
        cleanup_client_media(client_id)

        # Any other cleanup needed...
        await self.send_message(client_id, "Your post has been scheduled successfully!")

    async def send_scheduling_options(self, client_id: str) -> None:
        """Send scheduling options to the client"""
        buttons = [
            {"id": "later", "title": "Later Today"},
            {"id": "tomorrow", "title": "Tomorrow"},
            {"id": "next week", "title": "Next Week"},
            {"id": "now", "title": "Post Now"},
        ]

        await self.send_message(client_id, MESSAGES["schedule_prompt"])

        try:
            await self.client.send_interactive_buttons(
                header_text="Schedule Selection",
                body_text="When would you like to schedule your post?",
                buttons=buttons,
                phone_number=client_id,
            )
        except Exception as e:
            # Fallback to simple text message if buttons fail
            await self.send_message(
                client_id,
                "When would you like to schedule your post? Reply with 'now', 'later', 'tomorrow', or 'next week'.",
            )
            self.logger.error(f"Failed to send interactive buttons: {e}")

    async def send_media_gallery(
        self, client_id: str, media_items: List[MediaItem]
    ) -> None:
        """Send a media gallery to the client"""
        for item in media_items:
            await self.client.send_media(media_items=[item], phone_number=client_id)
