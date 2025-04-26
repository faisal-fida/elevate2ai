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

        self.state_manager.update_context(client_id, vars(context))

        # Send the generated content for approval
        await self.send_message(client_id, f"Here is the caption for the post: {caption}")
        await self.send_message(client_id, "Please select one of the images below:")

        # Send the media items as a gallery
        media_items = []
        for idx, url in enumerate(image_urls, 1):
            media_items.append(
                {"type": "image", "url": url, "caption": f"Reply with {idx} to select this image."}
            )

        await self.send_media_gallery(client_id, media_items)

        # Move to schedule selection
        self.state_manager.set_state(client_id, WorkflowState.SCHEDULE_SELECTION)

    async def send_media_gallery(self, client_id: str, media_items: List[MediaItem]) -> None:
        """Send a media gallery to the client"""
        for item in media_items:
            await self.client.send_media(media_items=[item], phone_number=client_id)
