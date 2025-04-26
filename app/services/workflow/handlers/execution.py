import asyncio
import random
from app.services.messaging.state_manager import WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import MESSAGES
from app.services.common.types import WorkflowContext
from app.services.content.canvas.switchboard import create_image


class ExecutionHandler(BaseHandler):
    """Handler for post execution state"""

    async def handle_confirmation(self, client_id: str, message: str) -> None:
        """Handle confirmation"""
        if message in ["yes", "y"]:
            # Move to post execution
            self.state_manager.set_state(client_id, WorkflowState.POST_EXECUTION)
            await self.handle(client_id, "")

        elif message in ["no", "n"]:
            # Reset the workflow
            self.state_manager.reset_client(client_id)
            await self.send_message(
                client_id, "Let's start over. Type 'Create Post' when you're ready."
            )

        else:
            await self.send_message(client_id, "Please reply with 'yes' or 'no'.")
            context = WorkflowContext(**self.state_manager.get_context(client_id))
            await self.send_confirmation_summary(client_id, context)

    async def handle(self, client_id: str, message: str) -> None:
        """Handle post execution"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Initialize platform-specific images dictionary if not exists
        if not hasattr(context, "platform_images") or context.platform_images is None:
            context.platform_images = {}

        # Generate platform-specific images using Switchboard Canvas
        await self.send_message(client_id, "Editing images for each platform...")

        try:
            for platform in context.selected_platforms:
                # Get the content type for this platform
                content_type = context.content_types.get(platform, context.selected_content_type)
                self.logger.info(
                    f"Generating image for {platform} with content type {content_type}"
                )

                try:
                    image_response = create_image(
                        client_id=client_id,
                        selected_url=context.selected_image,
                        caption=context.caption,
                        platform=platform,
                        post_type=content_type,
                    )

                    if image_response and "sizes" in image_response:
                        context.platform_images[platform] = image_response["sizes"][0]["url"]
                        self.logger.info(f"Successfully generated image for {platform}")
                    else:
                        self.logger.warning(f"No image URL returned for {platform}")
                        context.platform_images[platform] = context.selected_image

                except Exception as e:
                    self.logger.error(f"Error generating image for {platform}: {str(e)}")
                    context.platform_images[platform] = context.selected_image

            # Update context with generated images
            self.state_manager.update_context(client_id, vars(context))

            await self.send_message(client_id, "Here are the edited images for each platform:")
            for platform, image_url in context.platform_images.items():
                await self.client.send_media(
                    media_items=[{"type": "image", "url": image_url}],
                    phone_number=client_id,
                )

            # Now post the edited images to each platform with the caption
            await self.send_message(client_id, "Posting to selected platforms...")

            # In a real implementation, this would call APIs to post to each platform
            # For now, we'll simulate success/failure
            success_platforms = []
            failed_platforms = []

            for platform in context.selected_platforms:
                # Simulate 80% success rate
                if random.random() < 0.8:
                    success_platforms.append(platform)
                    if context.post_status is None:
                        context.post_status = {}
                    context.post_status[platform] = True
                else:
                    failed_platforms.append(platform)
                    if context.post_status is None:
                        context.post_status = {}
                    context.post_status[platform] = False

            self.state_manager.update_context(client_id, vars(context))

        except Exception as e:
            self.logger.error(f"Error in post execution: {str(e)}")
            await self.send_message(client_id, f"An error occurred: {str(e)}")
            failed_platforms = context.selected_platforms
            success_platforms = []

        # Send result message
        if success_platforms and not failed_platforms:
            # All platforms succeeded
            await self.send_message(
                client_id, MESSAGES["post_success"].format(platforms=", ".join(success_platforms))
            )
        elif success_platforms and failed_platforms:
            # Some platforms succeeded, some failed
            await self.send_message(
                client_id,
                MESSAGES["post_partial_success"].format(
                    success_platforms=", ".join(success_platforms),
                    failed_platforms=", ".join(failed_platforms),
                ),
            )
        else:
            # All platforms failed
            await self.send_message(client_id, MESSAGES["post_failure"])

        # Reset the workflow
        self.state_manager.reset_client(client_id)
        await self.send_message(
            client_id, "Type 'Create Post' when you're ready to create another post."
        )

    async def send_confirmation_summary(self, client_id: str, context: WorkflowContext) -> None:
        """Send confirmation summary to the client"""
        # Format platforms and content types
        platforms = ", ".join(context.selected_platforms)
        content_types = ", ".join([f"{p}: {t}" for p, t in context.content_types.items()])

        # Create summary message
        summary = MESSAGES["confirmation_summary"].format(
            platforms=platforms,
            content_types=content_types,
            schedule=context.schedule_time,
            caption=context.caption,
        )

        # Send the selected image with the summary
        await self.client.send_media(
            media_items=[{"type": "image", "url": context.selected_image, "caption": summary}],
            phone_number=client_id,
        )

        await asyncio.sleep(1)

        # Send confirmation buttons
        buttons = [{"id": "yes", "title": "Yes, Continue"}, {"id": "no", "title": "No, Start Over"}]

        await self.client.send_interactive_buttons(
            header_text="Confirmation",
            body_text=MESSAGES["editing_confirmation"],
            buttons=buttons,
            phone_number=client_id,
        )
