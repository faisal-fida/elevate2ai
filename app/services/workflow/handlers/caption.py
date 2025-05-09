from typing import List
from app.services.messaging.client import MessagingClient
from app.services.messaging.state_manager import StateManager, WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.services.content.generator import ContentGenerator
from app.constants import MESSAGES
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
        self.state_manager.update_context(client_id, vars(context))

        # Generate content based on the caption
        await self.send_message(client_id, MESSAGES["generating"])
        caption, image_urls = await self.content_generator.generate_content(message)

        # Update context with generated content
        context.caption = caption
        context.image_urls = image_urls

        # Set the first image as the default selected image
        if image_urls:
            context.selected_image = image_urls[0]

        # Ask about image inclusion right after generation
        context.waiting_for_image_decision = True
        self.state_manager.update_context(client_id, vars(context))

        # Send the generated caption first
        await self.send_message(
            client_id, f"Here is the caption for the post: {caption}"
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
