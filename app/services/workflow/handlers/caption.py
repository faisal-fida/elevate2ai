from typing import List, Dict, Any
from app.services.messaging.client import MessagingClient
from app.services.messaging.state_manager import StateManager, WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.services.content.generator import ContentGenerator
from app.constants import MESSAGES, TEMPLATE_CONFIG, SOCIAL_MEDIA_PLATFORMS
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
            await self.handle_media_selection(client_id, message)
            return

        # Handle template-specific input states
        current_state = self.state_manager.get_state(client_id)
        if current_state == WorkflowState.WAITING_FOR_DESTINATION:
            await self.handle_destination_input(client_id, message)
            return
        elif current_state == WorkflowState.WAITING_FOR_EVENT_NAME:
            await self.handle_event_name_input(client_id, message)
            return
        elif current_state == WorkflowState.WAITING_FOR_PRICE:
            await self.handle_price_input(client_id, message)
            return
        elif current_state == WorkflowState.WAITING_FOR_EVENT_IMAGE:
            await self.handle_event_image_input(client_id, message)
            return
        elif current_state == WorkflowState.MEDIA_SOURCE_SELECTION:
            await self.handle_media_source_selection(client_id, message)
            return
        elif current_state == WorkflowState.WAITING_FOR_MEDIA_UPLOAD:
            await self.handle_media_upload(client_id, message)
            return
        elif current_state == WorkflowState.VIDEO_SELECTION:
            await self.handle_video_selection(client_id, message)
            return

        if not message:
            await self.send_message(client_id, "Please enter a caption for your post.")
            return

        # Detect if this is video content
        is_video_content = self.is_video_content_type(context)
        context.is_video_content = is_video_content

        # Store the caption
        context.caption = message
        context.original_text = message
        self.state_manager.update_context(client_id, vars(context))

        # Check if we need to collect template-specific fields first
        if await self.request_template_fields(client_id):
            return  # Waiting for additional input

        # Generate content based on the caption
        await self.send_message(client_id, MESSAGES["generating"])

        try:
            if not context.template_id:
                # Find appropriate template
                for platform in context.selected_platforms:
                    template_id = (
                        self.content_generator.get_template_by_platform_and_type(
                            platform=platform,
                            content_type=context.selected_content_type,
                            client_id=client_id,
                        )
                    )
                    if template_id:
                        context.template_id = template_id
                        context.template_type = context.selected_content_type
                        break

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

                # Generate content using template
                (
                    caption,
                    media_urls,
                    template_data,
                ) = await self.content_generator.generate_template_content(
                    template_id=context.template_id, user_inputs=user_inputs
                )

                context.caption = caption

                if is_video_content:
                    # For video content, store in video_urls
                    context.video_urls = media_urls
                    if media_urls:
                        context.selected_video = media_urls[0]
                else:
                    # For image content, store in image_urls
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

        # Ask about media selection
        context.waiting_for_image_decision = True
        self.state_manager.update_context(client_id, vars(context))

        await self.ask_media_selection(client_id)

    def is_video_content_type(self, context: WorkflowContext) -> bool:
        """Check if the content type is video-based"""
        # Reels is always video content
        if context.selected_content_type == "reels":
            return True

        # Check platform-specific content types
        for platform in context.selected_platforms:
            if platform == "tiktok":
                return True  # TikTok is always video

            # Check content type for this platform
            platform_content_type = context.content_types.get(
                platform, context.selected_content_type
            )
            if platform_content_type in ["reels"]:
                return True

        # Check if template requires video_background
        if context.template_id:
            template = TEMPLATE_CONFIG["templates"].get(context.template_id, {})
            required_keys = template.get("required_keys", [])
            if "video_background" in required_keys:
                return True

        return False

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

        if "event_image" in required_keys and not context.event_image:
            self.state_manager.set_state(
                client_id, WorkflowState.WAITING_FOR_EVENT_IMAGE
            )
            await self.send_message(client_id, "Please upload an image for your event:")
            return True

        return False  # No additional inputs needed

    async def handle_destination_input(self, client_id: str, message: str) -> None:
        """Handle destination name input"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Validate the destination name
        is_valid, result = self.content_generator.openai_service.validate_user_input(
            message, max_words=5
        )

        if not is_valid:
            await self.send_message(client_id, result)
            return

        context.destination_name = result
        self.state_manager.update_context(client_id, vars(context))

        await self.send_message(client_id, f"Great! Destination name '{result}' saved.")

        # Return to caption input state and continue processing
        self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
        await self.handle(client_id, context.original_text)

    async def handle_event_name_input(self, client_id: str, message: str) -> None:
        """Handle event name input"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Validate the event name
        is_valid, result = self.content_generator.openai_service.validate_user_input(
            message, max_words=5
        )

        if not is_valid:
            await self.send_message(client_id, result)
            return

        context.event_name = result
        self.state_manager.update_context(client_id, vars(context))

        await self.send_message(client_id, f"Great! Event name '{result}' saved.")

        # Return to caption input state and continue processing
        self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
        await self.handle(client_id, context.original_text)

    async def handle_price_input(self, client_id: str, message: str) -> None:
        """Handle price input"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Store the price text
        context.price_text = message
        self.state_manager.update_context(client_id, vars(context))

        await self.send_message(
            client_id, f"Great! Price information '{message}' saved."
        )

        # Return to caption input state and continue processing
        self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
        await self.handle(client_id, context.original_text)

    async def handle_event_image_input(self, client_id: str, message: str) -> None:
        """Handle event image input"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # In a real implementation, this would handle an uploaded image
        # For now, assume the message contains a URL
        context.event_image = message
        self.state_manager.update_context(client_id, vars(context))

        await self.send_message(client_id, "Great! Event image saved.")

        # Return to caption input state and continue processing
        self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
        await self.handle(client_id, context.original_text)

    async def ask_media_selection(self, client_id: str) -> None:
        """Ask about media selection options"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Set the state for media selection
        self.state_manager.set_state(client_id, WorkflowState.MEDIA_SOURCE_SELECTION)

        # Use correct language based on content type
        media_type = "video" if context.is_video_content else "image"

        buttons = [
            {"id": "search_media", "title": f"Search for {media_type}"},
            {"id": "upload_media", "title": f"Upload my own {media_type}"},
        ]

        try:
            await self.client.send_interactive_buttons(
                header_text=f"{media_type.capitalize()} Selection",
                body_text=f"Would you like to search for a {media_type} or upload your own?",
                buttons=buttons,
                phone_number=client_id,
            )
        except Exception as e:
            # Fallback to simple text message
            await self.send_message(
                client_id,
                f"Would you like to search for a {media_type} or upload your own? Reply with 'search' or 'upload'.",
            )
            self.logger.error(f"Failed to send interactive buttons: {e}")

    async def handle_media_selection(self, client_id: str, message: str) -> None:
        """Handle media selection decision (replaces handle_image_decision)"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Clear the waiting flag
        context.waiting_for_image_decision = False
        self.state_manager.update_context(client_id, vars(context))

        # Redirect to the correct handler based on the updated flow
        await self.handle_media_source_selection(client_id, message)

    async def handle_media_source_selection(self, client_id: str, message: str) -> None:
        """Handle selection of media source (search vs upload)"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Handle both button responses and text responses
        if message.lower() in ["search_media", "search", "s"]:
            context.media_source = "search"
            self.state_manager.update_context(client_id, vars(context))

            # Show appropriate media options
            if context.is_video_content:
                await self.show_videos_for_selection(client_id)
            else:
                await self.show_images_for_selection(client_id)

        elif message.lower() in ["upload_media", "upload", "u"]:
            context.media_source = "upload"
            self.state_manager.update_context(client_id, vars(context))

            # Ask for upload
            self.state_manager.set_state(
                client_id, WorkflowState.WAITING_FOR_MEDIA_UPLOAD
            )

            # Use correct language based on content type
            media_type = "video" if context.is_video_content else "image"
            await self.send_message(
                client_id,
                f"Please upload your {media_type}. You can send it as an attachment.",
            )
        else:
            # Invalid response
            media_type = "video" if context.is_video_content else "image"
            await self.send_message(
                client_id,
                f"Please reply with 'search' to search for a {media_type} or 'upload' to upload your own.",
            )

    async def handle_media_upload(self, client_id: str, message: str) -> None:
        """Handle uploaded media"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # In a real implementation, this would process the uploaded media
        # For now, assume the message contains a URL to the uploaded media
        if context.is_video_content:
            context.selected_video = message
            context.video_background = message  # For template data
        else:
            context.selected_image = message

        self.state_manager.update_context(client_id, vars(context))

        media_type = "Video" if context.is_video_content else "Image"
        await self.send_message(client_id, f"{media_type} uploaded successfully!")

        # Move to scheduling
        self.state_manager.set_state(client_id, WorkflowState.SCHEDULE_SELECTION)
        await self.send_scheduling_options(client_id)

    async def show_images_for_selection(self, client_id: str) -> None:
        """Show images for the user to select from"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if we have images
        if not context.image_urls:
            await self.send_message(
                client_id,
                "Sorry, we couldn't find any images matching your criteria. Please upload your own.",
            )
            await self.handle_media_source_selection(client_id, "upload")
            return

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

    async def show_videos_for_selection(self, client_id: str) -> None:
        """Show videos for the user to select from"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if we have videos
        if not context.video_urls:
            await self.send_message(
                client_id,
                "Sorry, we couldn't find any videos matching your criteria. Please upload your own.",
            )
            await self.handle_media_source_selection(client_id, "upload")
            return

        # Set state for video selection
        self.state_manager.set_state(client_id, WorkflowState.VIDEO_SELECTION)

        # Send message to select a video
        await self.send_message(client_id, "Please select one of the videos below:")

        # In a real implementation, we would show video previews
        # For now, just list them with numbers
        options = "\n".join(
            [f"{i + 1}. Video Option {i + 1}" for i in range(len(context.video_urls))]
        )
        await self.send_message(
            client_id,
            f"Available videos:\n{options}\n\nReply with the number of your selection.",
        )

    async def handle_video_selection(self, client_id: str, message: str) -> None:
        """Handle video selection"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        try:
            selection = int(message.strip())
            if 1 <= selection <= len(context.video_urls):
                # Valid selection
                selected_video = context.video_urls[selection - 1]
                context.selected_video = selected_video
                context.video_background = selected_video  # For template data
                self.state_manager.update_context(client_id, vars(context))

                await self.send_message(client_id, f"Video {selection} selected!")

                # Move to scheduling
                self.state_manager.set_state(
                    client_id, WorkflowState.SCHEDULE_SELECTION
                )
                await self.send_scheduling_options(client_id)
            else:
                # Out of range
                await self.send_message(
                    client_id,
                    f"Please select a number between 1 and {len(context.video_urls)}.",
                )
        except ValueError:
            # Not a number
            await self.send_message(
                client_id, "Please reply with the number of the video you want to use."
            )

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
