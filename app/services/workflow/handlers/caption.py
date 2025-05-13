from typing import List
from app.services.messaging.client import MessagingClient
from app.services.messaging.state_manager import StateManager, WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.services.content.generator import ContentGenerator
from app.constants import MESSAGES, TEMPLATE_CONFIG
from app.services.common.types import WorkflowContext, MediaItem


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

        # Check if we're waiting for image inclusion decision
        if (
            hasattr(context, "waiting_for_image_decision")
            and context.waiting_for_image_decision
        ):
            await self.handle_image_decision(client_id, message)
            return

        if not message:
            await self.send_message(client_id, "Please enter a caption for your post.")
            return

        # Store the caption
        context.caption = message
        context.original_text = message

        # Check if we need to extract template-specific input fields
        if context.selected_content_type == "destination":
            # Treat the message as destination name
            is_valid, result = (
                self.content_generator.openai_service.validate_user_input(
                    message, max_words=5
                )
            )
            if not is_valid:
                await self.send_message(client_id, result)
                return

            context.destination_name = result
            await self.send_message(
                client_id, f"Great! Your destination '{result}' has been saved."
            )

        elif context.selected_content_type == "events":
            # Treat the message as event name
            is_valid, result = (
                self.content_generator.openai_service.validate_user_input(
                    message, max_words=5
                )
            )
            if not is_valid:
                await self.send_message(client_id, result)
                return

            context.event_name = result
            await self.send_message(
                client_id, f"Great! Your event '{result}' has been saved."
            )

        # Update context
        self.state_manager.update_context(client_id, vars(context))

        # Generate template-based content
        await self.send_message(client_id, MESSAGES["generating"])

        try:
            # Find a template to use based on platform and content type
            for platform in context.selected_platforms:
                # Get the template ID
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
                self.logger.warning(
                    f"No suitable template found for {context.selected_content_type}"
                )
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

                # Generate content using template
                (
                    caption,
                    image_urls,
                    template_data,
                ) = await self.content_generator.generate_template_content(
                    template_id=context.template_id, user_inputs=user_inputs
                )

                context.caption = caption
                context.image_urls = image_urls
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

        # Set the first image as the default selected image if we have images
        if context.image_urls:
            context.selected_image = context.image_urls[0]

        # Ask about image inclusion right after generation
        context.waiting_for_image_decision = True
        self.state_manager.update_context(client_id, vars(context))

        # Send the generated caption first
        await self.send_message(
            client_id, f"Here is the caption for the post: {context.caption}"
        )

        # Ask image inclusion question
        await self.ask_include_images(client_id)

    async def handle_image_decision(self, client_id: str, message: str) -> None:
        """Handle user's decision about including images"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Clear the waiting flag
        context.waiting_for_image_decision = False
        self.state_manager.update_context(client_id, vars(context))

        # Handle both button responses and text responses
        if message.lower() in ["yes_images", "yes", "y", "yes include images"]:
            context.include_images = True
            self.state_manager.update_context(client_id, vars(context))

            # Show images for selection
            await self.show_images_for_selection(client_id)
        elif message.lower() in ["no_images", "no", "n", "no caption only"]:
            context.include_images = False
            self.state_manager.update_context(client_id, vars(context))

            # Skip to scheduling without image selection
            self.state_manager.set_state(client_id, WorkflowState.SCHEDULE_SELECTION)
            await self.send_scheduling_options(client_id)
        else:
            # Invalid response, ask again
            context.waiting_for_image_decision = True
            self.state_manager.update_context(client_id, vars(context))
            await self.send_message(
                client_id,
                "Please reply with 'yes' to include images or 'no' for caption only.",
            )
            await self.ask_include_images(client_id)

    async def ask_include_images(self, client_id: str) -> None:
        """Ask user if they want to include images in the post"""
        buttons = [
            {"id": "yes_images", "title": "Yes, include images"},
            {"id": "no_images", "title": "No, caption only"},
        ]

        try:
            await self.client.send_interactive_buttons(
                header_text="Image Selection",
                body_text=MESSAGES["image_inclusion_prompt"],
                buttons=buttons,
                phone_number=client_id,
            )
        except Exception as e:
            # Fallback to simple text message
            await self.send_message(
                client_id,
                f"{MESSAGES['image_inclusion_prompt']} Reply with 'yes' to include images or 'no' for caption only.",
            )
            self.logger.error(
                f"Failed to send interactive buttons for image inclusion: {e}"
            )

    async def show_images_for_selection(self, client_id: str) -> None:
        """Show images for the user to select from"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Send message to select an image
        await self.send_message(client_id, "Please select one of the images below:")

        # Send the media items as a gallery
        media_items = []
        for idx, url in enumerate(context.image_urls, 1):
            media_items.append(
                {
                    "type": "image",
                    "url": url,
                    "caption": f"Reply with {idx} to select this image.",
                }
            )

        await self.send_media_gallery(client_id, media_items)

        # Move to schedule selection
        self.state_manager.set_state(client_id, WorkflowState.SCHEDULE_SELECTION)

    async def send_scheduling_options(self, client_id: str) -> None:
        """Send scheduling options to the client"""
        # Create buttons for scheduling options
        buttons = [
            {"id": "later", "title": "Later Today"},
            {"id": "tomorrow", "title": "Tomorrow"},
            {"id": "next week", "title": "Next Week"},
            {"id": "now", "title": "Post Now"},
        ]

        # Send message first to provide context
        await self.send_message(client_id, MESSAGES["schedule_prompt"])

        # Send interactive buttons (will automatically use list if > 3 buttons)
        await self.client.send_interactive_buttons(
            header_text="Schedule Selection",
            body_text="When would you like to schedule your post?",
            buttons=buttons,
            phone_number=client_id,
        )

    async def send_media_gallery(
        self, client_id: str, media_items: List[MediaItem]
    ) -> None:
        """Send a media gallery to the client"""
        for item in media_items:
            await self.client.send_media(media_items=[item], phone_number=client_id)

    async def request_additional_fields(self, client_id: str, template_id: str) -> None:
        """Request additional fields required by the template"""
        template = TEMPLATE_CONFIG["templates"].get(template_id, {})
        required_keys = template.get("required_keys", [])

        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if we need price information for promo templates
        if "price_text" in required_keys and not context.price_text:
            await self.send_message(
                client_id,
                "Please enter the price or promotion details (e.g., '$99', '50% off'):",
            )
            # Next message will be handled by a special state
            context.waiting_for_price = True
            self.state_manager.update_context(client_id, vars(context))
        # Check for other required fields as needed
        elif context.template_type == "destination" and not context.destination_name:
            await self.send_message(
                client_id, "Please enter the destination name (5 words or less):"
            )
        elif context.template_type == "events" and not context.event_name:
            await self.send_message(
                client_id, "Please enter the event name (5 words or less):"
            )
