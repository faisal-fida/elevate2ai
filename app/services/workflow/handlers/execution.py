import asyncio
import random
from app.services.messaging.state_manager import WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import MESSAGES
from app.services.common.types import WorkflowContext
from app.services.content.switchboard import create_image


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

    async def ask_include_images(self, client_id: str) -> None:
        """Ask user if they want to include images in the post"""
        buttons = [
            {"id": "yes_images", "title": "Yes, include images"},
            {"id": "no_images", "title": "No, caption only"},
        ]

        await self.client.send_interactive_buttons(
            header_text="Image Selection",
            body_text=MESSAGES["image_inclusion_prompt"],
            buttons=buttons,
            phone_number=client_id,
        )

    async def handle_image_decision(self, client_id: str, message: str) -> None:
        """Handle user's decision about including images"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if message in ["yes_images", "yes"]:
            context.include_images = True
            self.state_manager.update_context(client_id, vars(context))

            # Continue with generating images
            await self.generate_platform_images(client_id)
        elif message in ["no_images", "no"]:
            context.include_images = False
            self.state_manager.update_context(client_id, vars(context))

            # Skip image generation and proceed to posting with caption only
            await self.post_to_platforms(client_id)
        else:
            await self.send_message(client_id, "Please select one of the options.")
            await self.ask_include_images(client_id)

    async def handle(self, client_id: str, message: str) -> None:
        """Handle post execution"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if we're waiting for image inclusion decision
        if (
            hasattr(context, "waiting_for_image_decision")
            and context.waiting_for_image_decision
        ):
            await self.handle_image_decision(client_id, message)
            return

        # Initialize platform-specific images dictionary if not exists
        if not hasattr(context, "platform_images") or context.platform_images is None:
            context.platform_images = {}

        # Set the flag to indicate we're waiting for user's decision
        context.waiting_for_image_decision = True
        self.state_manager.update_context(client_id, vars(context))

        # Ask user if they want to include images
        await self.ask_include_images(client_id)

    async def generate_platform_images(self, client_id: str) -> None:
        """Generate images for each platform"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Clear the waiting flag
        context.waiting_for_image_decision = False
        self.state_manager.update_context(client_id, vars(context))

        # Generate platform-specific images using Switchboard Canvas
        await self.send_message(client_id, "Editing images for each platform...")

        try:
            for platform in context.selected_platforms:
                # Get the content type for this platform
                content_type = context.content_types.get(
                    platform, context.selected_content_type
                )
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
                        context.platform_images[platform] = image_response["sizes"][0][
                            "url"
                        ]
                        self.logger.info(f"Successfully generated image for {platform}")
                    else:
                        self.logger.warning(f"No image URL returned for {platform}")
                        context.platform_images[platform] = context.selected_image

                except Exception as e:
                    self.logger.error(
                        f"Error generating image for {platform}: {str(e)}"
                    )
                    context.platform_images[platform] = context.selected_image

            # Update context with generated images
            self.state_manager.update_context(client_id, vars(context))

            await self.send_message(
                client_id, "Here are the edited images for each platform:"
            )
            for platform, image_url in context.platform_images.items():
                await self.client.send_media(
                    media_items=[{"type": "image", "url": image_url}],
                    phone_number=client_id,
                )

            # Post to platforms with the images
            await self.post_to_platforms(client_id)

        except Exception as e:
            self.logger.error(f"Error in image generation: {str(e)}")
            await self.send_message(
                client_id, f"An error occurred during image generation: {str(e)}"
            )
            # Try to continue with posting anyway
            await self.post_to_platforms(client_id)

    async def post_to_platforms(self, client_id: str) -> None:
        """Post content to selected platforms"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Now post to each platform with or without images based on user's choice
        await self.send_message(client_id, "Posting to selected platforms...")

        # In a real implementation, this would call APIs to post to each platform
        # For now, we'll simulate success/failure
        success_platforms = []
        failed_platforms = []

        for platform in context.selected_platforms:
            # Here in a real implementation, you would check context.include_images
            # to determine whether to post with images or caption only
            has_images = getattr(context, "include_images", True)
            self.logger.info(f"Posting to {platform} with images: {has_images}")

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

        # Send result message
        if success_platforms and not failed_platforms:
            # All platforms succeeded
            await self.send_message(
                client_id,
                MESSAGES["post_success"].format(platforms=", ".join(success_platforms)),
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

    async def send_confirmation_summary(
        self, client_id: str, context: WorkflowContext
    ) -> None:
        """Send confirmation summary to the client"""
        # Format platforms and content types
        platforms = ", ".join(context.selected_platforms)
        content_types = ", ".join(
            [f"{p}: {t}" for p, t in context.content_types.items()]
        )

        # Create summary message
        summary = MESSAGES["confirmation_summary"].format(
            platforms=platforms,
            content_types=content_types,
            schedule=context.schedule_time,
            caption=context.caption,
        )

        # Send the selected image with the summary
        await self.client.send_media(
            media_items=[
                {"type": "image", "url": context.selected_image, "caption": summary}
            ],
            phone_number=client_id,
        )

        await asyncio.sleep(1)

        # Send confirmation buttons
        buttons = [
            {"id": "yes", "title": "Yes, Continue"},
            {"id": "no", "title": "No, Start Over"},
        ]

        await self.client.send_interactive_buttons(
            header_text="Confirmation",
            body_text=MESSAGES["editing_confirmation"],
            buttons=buttons,
            phone_number=client_id,
        )
