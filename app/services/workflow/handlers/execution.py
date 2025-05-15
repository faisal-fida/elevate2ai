import asyncio
import random
from app.services.messaging.client import MessagingClient
from app.services.messaging.state_manager import StateManager, WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import MESSAGES
from app.services.content.template_manager import template_manager
from app.services.common.types import WorkflowContext
from app.services.messaging.media_utils import cleanup_client_media
from app.services.content.switchboard import edit_media


class ExecutionHandler(BaseHandler):
    """Handler for post execution state"""

    def __init__(
        self,
        client: MessagingClient,
        state_manager: StateManager,
        scheduling_handler=None,
    ):
        super().__init__(client, state_manager)
        self.scheduling_handler = scheduling_handler

    async def handle_confirmation(self, client_id: str, message: str) -> None:
        """Handle confirmation"""
        if message in ["yes", "y"]:
            self.logger.info(
                f"User {client_id} confirmed the post, proceeding to execution"
            )

            # Move to post execution
            self.state_manager.set_state(client_id, WorkflowState.POST_EXECUTION)

            # Get the context to check content type
            context = WorkflowContext(**self.state_manager.get_context(client_id))

            # Determine if this is video-based content
            is_video_content = False
            if hasattr(context, "is_video_content"):
                is_video_content = context.is_video_content

            # Generate platform-specific media (images or videos)
            if is_video_content:
                await self.generate_platform_videos(client_id)
            else:
                await self.generate_platform_images(client_id)

        elif message in ["no", "n"]:
            # Reset the workflow
            self.state_manager.reset_client(client_id)
            await self.send_message(
                client_id, "Let's start over. Type 'Hi' when you're ready."
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

        try:
            await self.client.send_interactive_buttons(
                header_text="Image Selection",
                body_text=MESSAGES["image_inclusion_prompt"],
                buttons=buttons,
                phone_number=client_id,
            )
            self.logger.info(f"Successfully sent image inclusion prompt to {client_id}")
        except Exception as e:
            self.logger.error(f"Error sending image inclusion prompt: {str(e)}")
            # Fallback to simple text message
            await self.send_message(
                client_id,
                f"{MESSAGES['image_inclusion_prompt']} Reply with 'yes' to include images or 'no' for caption only.",
            )

    async def handle_image_decision(self, client_id: str, message: str) -> None:
        """Handle user's decision about including images"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        self.logger.info(f"Handling image decision for {client_id}, message: {message}")

        # Handle both button responses and text responses
        if message in ["yes_images", "yes", "y", "yes include images"]:
            context.include_images = True
            self.state_manager.update_context(client_id, context.model_dump())

            # Move to appropriate state for generating images
            self.state_manager.set_state(client_id, WorkflowState.POST_EXECUTION)

            # Continue with generating images
            await self.generate_platform_images(client_id)
        elif message in ["no_images", "no", "n", "no caption only"]:
            context.include_images = False
            self.state_manager.update_context(client_id, context.model_dump())

            # Move to post execution state for posting without images
            self.state_manager.set_state(client_id, WorkflowState.POST_EXECUTION)

            # Skip image generation and proceed to posting with caption only
            await self.post_to_platforms(client_id)
        else:
            self.logger.warning(f"Unrecognized response from {client_id}: {message}")
            await self.send_message(
                client_id,
                "Please reply with 'yes' to include images or 'no' for caption only.",
            )
            await self.ask_include_images(client_id)

    async def handle(self, client_id: str, message: str) -> None:
        """Handle post execution"""
        self.logger.info(
            f"ExecutionHandler.handle called for {client_id} with message: {message}"
        )

        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if this message might be part of another state's interaction
        if message.lower() in [
            "1",
            "2",
            "3",
            "4",
            "now",
            "later",
            "tomorrow",
            "next week",
        ]:
            if self.scheduling_handler is not None:
                self.state_manager.set_state(
                    client_id, WorkflowState.SCHEDULE_SELECTION
                )
                await self.scheduling_handler.handle(client_id, message)
                return
            else:
                self.logger.warning(
                    f"No scheduling handler available for {client_id}, unable to process message: {message}"
                )
                await self.send_message(
                    client_id,
                    "It seems like you're trying to schedule a post. Please try again later.",
                )
                return

        # Check if we should proceed with posting
        if message.lower() in ["post", "continue", "yes", "y"]:
            # Get the context to check if we're including images
            include_images = getattr(context, "include_images", True)

            if include_images:
                # If including images, generate platform-specific images
                await self.generate_platform_images(client_id)
            else:
                # If not including images, skip to posting
                await self.post_to_platforms(client_id)
        else:
            await self.send_message(
                client_id,
                "Type 'post' or 'continue' to proceed with posting your content.",
            )

    async def generate_platform_images(self, client_id: str) -> None:
        """Generate images for each platform"""
        self.logger.info(f"Starting generate_platform_images for {client_id}")
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Clear the waiting flag
        context.waiting_for_image_decision = False
        self.logger.info(f"Setting waiting_for_image_decision=False for {client_id}")
        self.state_manager.update_context(client_id, context.model_dump())

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
                    # Prepare template data
                    template_data = {
                        "main_image": context.selected_image,
                        "caption_text": context.caption,
                    }

                    # Add context-specific data
                    if (
                        hasattr(context, "destination_name")
                        and context.destination_name
                    ):
                        template_data["destination_name"] = context.destination_name

                    if hasattr(context, "event_name") and context.event_name:
                        template_data["event_name"] = context.event_name

                    if hasattr(context, "price_text") and context.price_text:
                        template_data["price_text"] = context.price_text

                    # Add event_image if it exists
                    if hasattr(context, "event_image") and context.event_image:
                        template_data["event_image"] = context.event_image
                    # If event_image is required but not set, use selected_image
                    elif context.selected_image:
                        # Use a default template ID for compatibility
                        template_client_id = (
                            "351915950259"  # Default template client ID
                        )
                        template_id = f"{platform}_{template_client_id}_{content_type}"
                        if "event_image" in template_manager.get_required_keys(
                            template_id
                        ):
                            template_data["event_image"] = context.selected_image
                            self.logger.info(
                                "Using selected_image as event_image for template compatibility"
                            )

                    # Validate inputs for this template
                    # Use the default template ID for validation
                    template_client_id = "351915950259"  # Default template client ID
                    template_id = f"{platform}_{template_client_id}_{content_type}"
                    is_valid, error_message, validated_data = (
                        template_manager.validate_inputs(template_id, template_data)
                    )

                    if not is_valid:
                        self.logger.warning(f"Invalid template data: {error_message}")
                        await self.send_message(
                            client_id,
                            f"Could not generate content for {platform}: {error_message}",
                        )
                        continue

                    # Build final template payload
                    template_payload = template_manager.build_payload(
                        template_id, validated_data
                    )

                    # Create image with Switchboard
                    image_response = edit_media(
                        client_id=client_id,
                        template_data=template_payload,
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

                except ValueError as ve:
                    self.logger.error(f"Template validation error for {platform}: {ve}")
                    await self.send_message(
                        client_id, f"Error with template data for {platform}: {ve}"
                    )
                    context.platform_images[platform] = context.selected_image
                except Exception as e:
                    self.logger.error(
                        f"Error generating image for {platform}: {str(e)}"
                    )
                    context.platform_images[platform] = context.selected_image

            # Update context with generated images
            self.state_manager.update_context(client_id, context.model_dump())

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

    async def generate_platform_videos(self, client_id: str) -> None:
        """Generate videos for each platform"""
        self.logger.info(f"Starting generate_platform_videos for {client_id}")
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Generate platform-specific videos using Switchboard Canvas
        await self.send_message(client_id, "Editing videos for each platform...")

        try:
            for platform in context.selected_platforms:
                # Get the content type for this platform
                content_type = context.content_types.get(
                    platform, context.selected_content_type
                )
                self.logger.info(
                    f"Generating video for {platform} with content type {content_type}"
                )

                try:
                    # Prepare template data
                    template_data = {
                        "caption_text": context.caption,
                    }

                    # Add video background if available
                    if context.selected_video:
                        template_data["video_background"] = context.selected_video

                    # Add context-specific data
                    if (
                        hasattr(context, "destination_name")
                        and context.destination_name
                    ):
                        template_data["destination_name"] = context.destination_name

                    if hasattr(context, "event_name") and context.event_name:
                        template_data["event_name"] = context.event_name

                    if hasattr(context, "price_text") and context.price_text:
                        template_data["price_text"] = context.price_text

                    # Add event_image if it exists
                    if hasattr(context, "event_image") and context.event_image:
                        template_data["event_image"] = context.event_image

                    # Validate inputs for this template
                    # Use the default template ID for validation
                    template_client_id = "351915950259"  # Default template client ID
                    template_id = f"{platform}_{template_client_id}_{content_type}"
                    is_valid, error_message, validated_data = (
                        template_manager.validate_inputs(template_id, template_data)
                    )

                    if not is_valid:
                        self.logger.warning(f"Invalid template data: {error_message}")
                        await self.send_message(
                            client_id,
                            f"Could not generate content for {platform}: {error_message}",
                        )
                        continue

                    # Build final template payload
                    template_payload = template_manager.build_payload(
                        template_id, validated_data
                    )

                    # Create video with Switchboard
                    video_response = edit_media(
                        client_id=client_id,
                        template_data=template_payload,
                        platform=platform,
                        post_type=content_type,
                    )

                    if video_response and "sizes" in video_response:
                        context.platform_images[platform] = video_response["sizes"][0][
                            "url"
                        ]
                        self.logger.info(f"Successfully generated video for {platform}")
                    else:
                        self.logger.warning(f"No video URL returned for {platform}")
                        context.platform_images[platform] = context.selected_video

                except ValueError as ve:
                    self.logger.error(f"Template validation error for {platform}: {ve}")
                    await self.send_message(
                        client_id, f"Error with template data for {platform}: {ve}"
                    )
                    if context.selected_video:
                        context.platform_images[platform] = context.selected_video
                except Exception as e:
                    self.logger.error(
                        f"Error generating video for {platform}: {str(e)}"
                    )
                    if context.selected_video:
                        context.platform_images[platform] = context.selected_video

            # Update context with generated videos
            self.state_manager.update_context(client_id, context.model_dump())

            await self.send_message(
                client_id, "Here are the edited videos for each platform:"
            )
            for platform, video_url in context.platform_images.items():
                await self.client.send_media(
                    media_items=[{"type": "video", "url": video_url}],
                    phone_number=client_id,
                )

            # Post to platforms with the videos
            await self.post_to_platforms(client_id)

        except Exception as e:
            self.logger.error(f"Error in video generation: {str(e)}")
            await self.send_message(
                client_id, f"An error occurred during video generation: {str(e)}"
            )
            # Try to continue with posting anyway
            await self.post_to_platforms(client_id)

    async def post_to_platforms(self, client_id: str) -> None:
        """Post content to selected platforms"""
        self.logger.info(f"Starting post_to_platforms for {client_id}")
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Make sure we're in POST_EXECUTION state
        self.state_manager.set_state(client_id, WorkflowState.POST_EXECUTION)

        # Determine if this is a video-based content
        is_video_content = getattr(context, "is_video_content", False)
        media_type = "video" if is_video_content else "image"

        self.logger.info(f"Posting for {client_id} with {media_type} content type")

        # Now post to each platform with the appropriate media type
        await self.send_message(
            client_id, f"Posting {media_type} content to selected platforms..."
        )

        # In a real implementation, this would call APIs to post to each platform
        # For now, we'll simulate success/failure
        success_platforms = []
        failed_platforms = []

        for platform in context.selected_platforms:
            # Get media URL with fallbacks
            media_url = context.platform_images.get(platform)

            # If no platform-specific image, use the selected image/video
            if not media_url:
                if is_video_content and context.selected_video:
                    media_url = context.selected_video
                elif context.selected_image:
                    media_url = context.selected_image

            self.logger.info(
                f"Posting to {platform} with {media_type} URL: {media_url}"
            )

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

        self.state_manager.update_context(client_id, context.model_dump())

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

        # Clean up media files for this client
        cleanup_client_media(client_id)
        self.logger.info(f"Media files cleaned up for client {client_id}")

        # Reset the workflow
        self.state_manager.reset_client(client_id)
        await self.send_message(
            client_id, "Type 'Hi' when you're ready to create another post."
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

        # Determine if this is video content
        is_video_content = getattr(context, "is_video_content", False)

        # Send the selected media with the summary
        if is_video_content and context.selected_video:
            await self.client.send_media(
                media_items=[
                    {"type": "video", "url": context.selected_video, "caption": summary}
                ],
                phone_number=client_id,
            )
        elif context.selected_image:
            await self.client.send_media(
                media_items=[
                    {"type": "image", "url": context.selected_image, "caption": summary}
                ],
                phone_number=client_id,
            )
        else:
            # Just send the text summary if no media is available
            await self.send_message(client_id, summary)

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
