from __future__ import annotations
import asyncio
from app.services.messaging.whatsapp import WhatsApp
from app.services.messaging.state_manager import StateManager, WorkflowState
from app.constants import MESSAGES
from app.services.content.contexts.base_context import PromoWorkflowContext
from app.services.content.handlers.base_handler import BaseHandler
from app.services.content.generator import ContentGenerator
from app.services.content.switchboard_canvas import create_image


class PromoHandler(BaseHandler):
    """Handler for the promotional content workflow."""

    def __init__(
        self,
        whatsapp: WhatsApp,
        state_manager: StateManager,
        content_generator: ContentGenerator,
        social_media_handler=None,  # Will be set after initialization to avoid circular imports
    ):
        super().__init__(whatsapp, state_manager, PromoWorkflowContext)
        self.content_generator = content_generator
        self.social_media_handler = social_media_handler

    async def _generate_and_send_gallery(self, client_id: str, text: str) -> PromoWorkflowContext:
        """Generate content and send a gallery of images to the client."""
        media_items = []

        # Generate content using the ContentGenerator
        caption, image_urls = await self.content_generator.generate_content(text)
        context = PromoWorkflowContext(caption=caption, image_urls=image_urls, original_text=text)
        await self._send_message(client_id, f"Here is the caption for the post: {caption}")
        await self._send_message(client_id, "Please select one of the images below:")

        # Send the media items as a gallery
        for idx, url in enumerate(image_urls, 1):
            media_items.append(
                {"type": "image", "url": url, "caption": f"Reply with {idx} to select this image."}
            )

        self.logger.info(f"Sending media items to {client_id}")
        await self.whatsapp.send_media(media_items=media_items, phone_number=client_id)
        await asyncio.sleep(1)
        await self._send_message(
            client_id,
            "Reply with the number (1-4) to select an image, or type 'regenerate' for a new set.",
        )
        return context

    async def handle_init(self, client_id: str, message: str) -> None:
        """Handle the initial message from the client."""
        if message == "hi":
            await self._send_message(client_id, MESSAGES["welcome"])
            self.set_state(client_id, WorkflowState.WAITING_FOR_PROMO)
        elif message == "create post" and self.social_media_handler:
            # Initialize the social media posting workflow
            await self._send_message(client_id, MESSAGES["create_post_welcome"])
            await self.social_media_handler.start_workflow(client_id)
        else:
            await self._send_message(client_id, MESSAGES["start_prompt"])

    async def handle_promo_text(self, client_id: str, message: str) -> None:
        """Handle the promo text message from the client."""
        await self._send_message(client_id, MESSAGES["generating"])
        context = await self._generate_and_send_gallery(client_id, message)
        self.update_context(client_id, context)
        self.set_state(client_id, WorkflowState.WAITING_FOR_APPROVAL)

    async def handle_approval(self, client_id: str, message: str) -> None:
        """Handle the approval message from the client."""
        context = self.get_context(client_id)

        if message in {"regenerate", "n"}:
            await self._send_message(client_id, MESSAGES["regenerating"])
            new_context = await self._generate_and_send_gallery(client_id, context.original_text)
            self.update_context(client_id, new_context)
        elif message in {"1", "2", "3", "4"}:
            idx = int(message) - 1
            if 0 <= idx < len(context.image_urls):
                selected_url = context.image_urls[idx]
                await self.whatsapp.send_media(
                    media_items={"type": "image", "url": selected_url, "caption": context.caption},
                    phone_number=client_id,
                )
                await self._send_message(client_id, MESSAGES["finalized"])

                # Generate the final image using Switchboard Canvas
                create_image(
                    client_id=client_id,
                    selected_url=selected_url,
                    caption=context.caption,
                    platform="instagram",
                    post_type="travel",
                )

                # Reset the state and context
                self.state_manager.reset_client(client_id)

                # Start the social media posting workflow if handler is available
                if self.social_media_handler:
                    await self.social_media_handler.start_workflow(client_id)
            else:
                await self._send_message(
                    client_id, "Invalid number. Please reply with 1, 2, 3, or 4."
                )
        else:
            await self._send_message(client_id, "Please reply with 1, 2, 3, 4, or 'regenerate'.")
