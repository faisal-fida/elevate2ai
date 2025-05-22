from typing import List, Optional
from app.services.messaging.client import MessagingClient
from app.services.messaging.state_manager import StateManager, WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.services.content.generator import ContentGenerator
from app.constants import MESSAGES
from app.services.content.template_service import template_service
from app.services.content.template_config import (
    FieldSource,
    get_field_config,
    get_template_config,
    get_required_keys,
)
from app.services.types import WorkflowContext, MediaItem
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
        from app.services.content.image_service import MediaService

        self.media_service = MediaService()

    async def handle(self, client_id: str, message: str) -> None:
        """Handle caption input"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if we're waiting for image upload or selection
        current_state = self.state_manager.get_state(client_id)
        if current_state == WorkflowState.WAITING_FOR_MEDIA_UPLOAD:
            await self.handle_media_upload(client_id, message)
            return
        elif current_state == WorkflowState.IMAGE_SELECTION:
            await self.handle_image_selection(client_id, message)
            return
        elif current_state == WorkflowState.VIDEO_SELECTION:
            await self.handle_video_selection(client_id, message)
            return
        elif current_state == WorkflowState.WAITING_FOR_CAPTION:
            await self.handle_waiting_for_caption(client_id, message)
            return
        elif current_state == WorkflowState.WAITING_FOR_DESTINATION:
            await self.handle_destination_input(client_id, message)
            return
        elif current_state == WorkflowState.WAITING_FOR_PRICE:
            await self.handle_price_input(client_id, message)
            return

        if not message:
            # If no template-specific fields needed, ask for general caption
            await self.send_message(client_id, MESSAGES["caption_prompt"])
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
                    self.state_manager.update_context(client_id, context.model_dump())
                    break

        # For promo templates, collect required fields first
        if context.selected_content_type == "promo":
            # Ask for destination name if not provided
            if not context.destination_name:
                self.state_manager.set_state(
                    client_id, WorkflowState.WAITING_FOR_DESTINATION
                )
                await self.send_message(
                    client_id, "Please enter the destination name (5 words or less):"
                )
                return
            # Ask for price if not provided
            elif not context.price_text:
                self.state_manager.set_state(client_id, WorkflowState.WAITING_FOR_PRICE)
                await self.send_message(
                    client_id,
                    "Please enter the price or promotion details (e.g., '$99', '50% off'):",
                )
                return

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
                    "destination_name": context.destination_name,
                    "price_text": context.price_text,
                }

                # Add any existing media to user_inputs
                if context.selected_image:
                    user_inputs["main_image"] = context.selected_image
                if context.selected_video:
                    user_inputs["video_background"] = context.selected_video

                # Generate content using template
                (
                    caption,
                    media_urls,
                    template_data,
                ) = await self.content_generator.generate_template_content(
                    template_id=context.template_id, user_inputs=user_inputs
                )

                context.caption = caption
                if media_urls:
                    context.image_urls = media_urls
                context.template_data = template_data

            # CRITICAL: Update the state manager with the modified context
            self.state_manager.update_context(client_id, context.model_dump())

            # Send the generated caption
            await self.send_message(
                client_id, f"Here is the caption for the post: {context.caption}"
            )

            # Ask for appropriate media based on platform
            await self.ask_for_media_upload(client_id)

        except Exception as e:
            self.logger.error(f"Error generating content: {e}")
            await self.send_message(client_id, f"Error generating content: {e}")
            # Reset to caption input state
            self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)

    async def request_template_fields(self, client_id: str) -> bool:
        """
        Request any template-specific fields that are required.
        Returns True if waiting for additional input.
        """
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Find template if not already set
        if not context.template_id:
            for platform in context.selected_platforms:
                # Use the template service to get the template ID
                template_id = template_service.get_template_id(
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

        # Extract platform and content_type from template_id
        parts = context.template_id.split("_")
        if len(parts) >= 3:
            platform = parts[0]
            content_type = parts[2]

            # Skip caption_text field if we already have a caption
            if context.caption:
                # Store caption in template_data to prevent re-requesting
                if not context.template_data:
                    context.template_data = {}
                context.template_data["caption_text"] = context.caption
                self.state_manager.update_context(client_id, context.model_dump())
                return False

            # Use the template service to get the next field to collect
            next_field = template_service.get_next_field_to_collect(
                platform=platform, content_type=content_type, context=context
            )

            if next_field:
                field_name, workflow_state, prompt = next_field

                # Skip if we already have this field in template_data
                if context.template_data and field_name in context.template_data:
                    return False

                self.logger.info(
                    f"Requesting field {field_name} for {platform}_{content_type}"
                )

                # Set the state and send the prompt
                self.state_manager.set_state(client_id, workflow_state)
                await self.send_message(client_id, prompt)
                return True

        return False  # No additional inputs needed

    async def handle_destination_input(self, client_id: str, message: str) -> None:
        """Handle destination name input"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if this is a media message
        context_data = self.state_manager.get_context(client_id)
        if context_data.get("is_media_message", False) or message.startswith(
            "MEDIA_MESSAGE:"
        ):
            # This is a media message, not a destination name
            await self.send_message(
                client_id,
                "I need a text name for your destination, not a media file. Please enter the destination name (5 words or less):",
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

        # Check if this is a media message
        context_data = self.state_manager.get_context(client_id)
        if context_data.get("is_media_message", False) or message.startswith(
            "MEDIA_MESSAGE:"
        ):
            # This is a media message, not an event name
            await self.send_message(
                client_id,
                "I need a text name for your event, not a media file. Please enter the event name (5 words or less):",
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

        # Get template config to determine next state
        parts = context.template_id.split("_")
        if len(parts) >= 3:
            platform = parts[0]
            content_type = parts[2]
            template_config = get_template_config(platform, content_type)

            if template_config:
                field_config = template_config.fields.get("event_name")
                if field_config and field_config.next_state:
                    self.state_manager.set_state(
                        client_id, WorkflowState[field_config.next_state]
                    )
                    # Get next field based on dependencies
                    next_field = template_config.get_next_required_field(
                        ["main_image", "event_name"]
                    )
                    if next_field and next_field in template_config.fields:
                        await self.send_message(
                            client_id,
                            template_config.fields[next_field].prompt
                            or "Please provide the next required information.",
                        )
                    return

        # If no specific next state, return to caption input
        self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
        await self.handle(client_id, context.original_text)

    async def handle_price_input(self, client_id: str, message: str) -> None:
        """Handle price input"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if this is a media message
        context_data = self.state_manager.get_context(client_id)
        if context_data.get("is_media_message", False) or message.startswith(
            "MEDIA_MESSAGE:"
        ):
            # This is a media message, not a price
            await self.send_message(
                client_id,
                "I need text for your price information, not a media file. Please enter the price or promotion details (e.g., '$99', '50% off'):",
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

    async def handle_headline_input(self, client_id: str, message: str) -> None:
        """Handle headline input for seasonal templates"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if this is a media message
        context_data = self.state_manager.get_context(client_id)
        if context_data.get("is_media_message", False) or message.startswith(
            "MEDIA_MESSAGE:"
        ):
            # This is a media message, not a headline
            await self.send_message(
                client_id,
                "I need text for your theme, not a media file. Please provide a theme or topic for your seasonal post (5 words or less):",
            )
            return

        # Validate the headline text
        is_valid, result = self.content_generator.openai_service.validate_user_input(
            message, max_words=30
        )

        if not is_valid:
            await self.send_message(client_id, result)
            return

        # Store the headline as caption_text in the context
        context.caption = result
        context.original_text = result

        # Also store it in template_data to prevent it from being requested again
        if not context.template_data:
            context.template_data = {}
        context.template_data["caption_text"] = result

        self.state_manager.update_context(client_id, context.model_dump())

        await self.send_message(
            client_id, f"Great! I'll use '{result}' as the theme for your post."
        )

        # Generate content based on the headline
        await self.send_message(client_id, MESSAGES["generating"])

        try:
            # Prepare user inputs for template
            user_inputs = {
                "caption_text": result,  # Use the headline as caption_text
            }

            # Generate content using template
            (
                caption,
                media_urls,
                template_data,
            ) = await self.content_generator.generate_template_content(
                template_id=context.template_id, user_inputs=user_inputs
            )

            context.caption = caption

            # Make sure we store the media URLs properly
            if media_urls and len(media_urls) > 0:
                self.logger.info(
                    f"Storing {len(media_urls)} media URLs in context for headline"
                )
                context.image_urls = media_urls
                context.selected_image = media_urls[0]

                # Also store media options in template_data if not already there
                if template_data and "media_options" not in template_data:
                    template_data["media_options"] = media_urls

            context.template_data = template_data
            self.state_manager.update_context(client_id, context.model_dump())

            # Send the generated caption
            await self.send_message(
                client_id,
                f"Here is the caption for the post in headline_input: {context.caption}",
            )

            # Check if we need to ask for image upload or use external service
            await self.ask_for_media_upload(client_id)

        except Exception as e:
            self.logger.error(f"Error generating content: {e}")
            await self.send_message(client_id, f"Error generating content: {e}")
            # Reset to caption input state
            self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)

    async def ask_for_media_upload(self, client_id: str) -> None:
        """Ask the user to upload an image or search for one based on template configuration"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if we have a template ID
        if context.template_id:
            # Extract platform and content_type from template_id
            parts = context.template_id.split("_")
            if len(parts) >= 3:
                platform = parts[0]
                content_type = parts[2]

                # Get the field config for main_image
                field_config = get_field_config(platform, content_type, "main_image")

                if field_config:
                    # Check if the image should come from an external service
                    if field_config.source == FieldSource.EXTERNAL_SERVICE:
                        self.logger.info(
                            f"Using external service for image in {platform}_{content_type}"
                        )

                        # Send the appropriate message from the template config
                        if field_config.prompt:
                            await self.send_message(client_id, field_config.prompt)
                        else:
                            await self.send_message(
                                client_id,
                                "Here are some images for your post. Please select one:",
                            )

                        # Generate optimized search query using OpenAI
                        search_query = await self.content_generator.openai_service.generate_image_search_query(
                            template_type=content_type,
                            context={
                                "caption": context.caption,
                                "destination_name": getattr(
                                    context, "destination_name", ""
                                ),
                                "event_name": getattr(context, "event_name", ""),
                            },
                        )

                        try:
                            image_urls = await self.content_generator.media_service.search_images(
                                search_query, limit=4
                            )
                            if image_urls and len(image_urls) > 0:
                                context.image_urls = image_urls
                                if not context.template_data:
                                    context.template_data = {}
                                context.template_data["media_options"] = image_urls
                                self.state_manager.update_context(
                                    client_id, context.model_dump()
                                )

                                # Show images for selection
                                max_images = min(4, len(image_urls))
                                for i in range(max_images):
                                    image_url = image_urls[i]
                                    await self.client.send_media(
                                        {
                                            "type": "image",
                                            "url": image_url,
                                            "caption": f"Option {i + 1}",
                                        },
                                        client_id,
                                    )

                                # Update state for image selection
                                self.state_manager.set_state(
                                    client_id, WorkflowState.IMAGE_SELECTION
                                )
                                await self.send_message(
                                    client_id,
                                    "Please reply with the number of the image you want to use (1-4).",
                                )
                                return
                        except Exception as e:
                            self.logger.error(f"Error searching for images: {e}")

                    # If it's USER_INPUT, ask for upload with the configured prompt
                    elif field_config.source == FieldSource.USER_INPUT:
                        self.state_manager.set_state(
                            client_id, WorkflowState.WAITING_FOR_MEDIA_UPLOAD
                        )
                        if field_config.prompt:
                            await self.send_message(client_id, field_config.prompt)
                        else:
                            await self.send_message(
                                client_id, "Please upload an image for your post."
                            )
                        return

        # Default behavior if no template or no specific configuration
        self.state_manager.set_state(client_id, WorkflowState.WAITING_FOR_MEDIA_UPLOAD)
        await self.send_message(client_id, "Please upload an image for your post.")

    async def handle_media_upload(self, client_id: str, message: str) -> None:
        """Handle media upload from WhatsApp"""
        try:
            context = WorkflowContext(**self.state_manager.get_context(client_id))

            # Process media message
            if message.startswith("MEDIA_MESSAGE:"):
                parts = message.split(":")
                if len(parts) >= 3:
                    media_type = parts[1]
                    media_id = parts[2]

                    # Get template configuration if available
                    if context.template_id:
                        parts = context.template_id.split("_")
                        if len(parts) >= 3:
                            platform = parts[0]
                            content_type = parts[2]
                            template_config = get_template_config(
                                platform, content_type
                            )

                            if template_config:
                                # Check if media type matches platform requirements
                                is_video_required = (
                                    template_config.is_video
                                    or "video_background" in template_config.fields
                                )
                                if is_video_required and media_type != "video":
                                    await self.send_message(
                                        client_id,
                                        f"This {platform} {content_type} post requires a video. Please upload a video file.",
                                    )
                                    return
                                elif not is_video_required and media_type != "image":
                                    await self.send_message(
                                        client_id,
                                        f"This {platform} {content_type} post requires an image. Please upload an image file.",
                                    )
                                    return

                    # Process the media upload
                    media_url = await self._process_media_upload(
                        client_id, media_id, media_type
                    )
                    if not media_url:
                        await self.send_message(
                            client_id,
                            "Sorry, there was an error processing your media upload. Please try again.",
                        )
                        return

                    # Store the media URL based on type
                    if media_type == "video":
                        context.selected_video = media_url
                        context.video_background = media_url
                        if not context.template_data:
                            context.template_data = {}
                        context.template_data["video_background"] = media_url
                    else:
                        context.selected_image = media_url
                        context.main_image = media_url
                        if not context.template_data:
                            context.template_data = {}
                        context.template_data["main_image"] = media_url

                    self.state_manager.update_context(client_id, context.model_dump())

                    # Get template configuration if available
                    if context.template_id:
                        parts = context.template_id.split("_")
                        if len(parts) >= 3:
                            platform = parts[0]
                            content_type = parts[2]
                            template_config = get_template_config(
                                platform, content_type
                            )

                            if template_config:
                                # Check if all required fields are collected
                                required_fields = get_required_keys(
                                    platform, content_type
                                )
                                missing_fields = []

                                for field in required_fields:
                                    if field == "main_image" and context.selected_image:
                                        continue
                                    if (
                                        field == "video_background"
                                        and context.selected_video
                                    ):
                                        continue
                                    if field == "caption_text" and context.caption:
                                        continue
                                    if (
                                        field == "destination_name"
                                        and context.destination_name
                                    ):
                                        continue
                                    if field == "price_text" and context.price_text:
                                        continue
                                    missing_fields.append(field)

                                if missing_fields:
                                    # Ask for the next required field
                                    if "destination_name" in missing_fields:
                                        self.state_manager.set_state(
                                            client_id,
                                            WorkflowState.WAITING_FOR_DESTINATION,
                                        )
                                        await self.send_message(
                                            client_id,
                                            "Please enter the destination name (5 words or less):",
                                        )
                                        return
                                    elif "price_text" in missing_fields:
                                        self.state_manager.set_state(
                                            client_id, WorkflowState.WAITING_FOR_PRICE
                                        )
                                        await self.send_message(
                                            client_id,
                                            "Please enter the price or promotion details (e.g., '$99', '50% off'):",
                                        )
                                        return

                # If all required fields are collected or no template config, move to scheduling
                self.state_manager.set_state(
                    client_id, WorkflowState.SCHEDULE_SELECTION
                )
                await self.send_scheduling_options(client_id)

        except Exception as e:
            self.logger.error(f"Error processing media upload: {e}")
            await self.send_message(
                client_id,
                "Sorry, there was an error processing your media upload. Please try again.",
            )

    async def _process_media_upload(
        self, client_id: str, media_id: str, media_type: str
    ) -> Optional[str]:
        """Process media upload and return public URL"""
        try:
            if media_type == "video":
                # Get template configuration
                context = WorkflowContext(**self.state_manager.get_context(client_id))
                if context.template_id:
                    parts = context.template_id.split("_")
                    if len(parts) >= 3:
                        platform = parts[0]
                        content_type = parts[2]
                        template_config = get_template_config(platform, content_type)

                        if template_config and template_config.is_video:
                            # For external service videos, we should already have the video URL
                            if (
                                "video_background" in template_config.fields
                                and template_config.fields["video_background"].source
                                == FieldSource.EXTERNAL_SERVICE
                            ):
                                return (
                                    context.video_background or context.selected_video
                                )

                # For user uploaded videos
                return await self._save_whatsapp_video(media_id)
            else:
                # Use existing image upload handling
                return await save_whatsapp_image(media_id, client_id)
        except Exception as e:
            self.logger.error(f"Error processing media upload: {e}")
            return None

    async def _save_whatsapp_video(self, media_id: str) -> Optional[str]:
        """Save video from WhatsApp"""
        # TODO: Implement video saving logic
        # For now, return a placeholder
        return f"/media/videos/{media_id}.mp4"

    async def handle_image_selection(self, client_id: str, message: str) -> None:
        """Handle image selection from the options presented to the user"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if we have image URLs in the context
        if not context.image_urls or len(context.image_urls) == 0:
            self.logger.error(f"No image URLs found in context for {client_id}")
            await self.send_message(
                client_id,
                "Sorry, there was an error with the image selection. Please try again.",
            )
            self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
            return

        # Try to parse the selection as a number
        try:
            # Clean up the message (remove any non-numeric characters)
            selection = "".join(filter(str.isdigit, message))
            if not selection:
                raise ValueError("No numeric selection found")

            selection_num = int(selection)

            # Check if the selection is valid
            if selection_num < 1 or selection_num > len(context.image_urls):
                await self.send_message(
                    client_id,
                    f"Please select a valid option between 1 and {len(context.image_urls)}.",
                )
                return

            # Get the selected image URL
            try:
                selected_image = context.image_urls[selection_num - 1]
                # Make sure the URL is valid
                if not selected_image or not isinstance(selected_image, str):
                    raise ValueError(f"Invalid image URL: {selected_image}")
            except (IndexError, ValueError) as e:
                self.logger.error(f"Error getting selected image: {e}")
                await self.send_message(
                    client_id,
                    "Sorry, there was an error with your selection. Please try again or upload your own image.",
                )
                self.state_manager.set_state(
                    client_id, WorkflowState.WAITING_FOR_MEDIA_UPLOAD
                )
                return

            # Store the selected image in the context
            context.selected_image = selected_image

            # Update template_data if it exists
            if not context.template_data:
                context.template_data = {}

            # Determine the appropriate field name based on template
            if context.template_id:
                parts = context.template_id.split("_")
                if len(parts) >= 3:
                    platform = parts[0]
                    content_type = parts[2]

                    # Check if this is a video-based template
                    is_video_platform = platform.lower() == "tiktok"
                    template_config = get_template_config(platform, content_type)
                    required_keys = template_service.get_required_fields(
                        platform, content_type
                    )

                    is_video_content = (
                        "video_background" in required_keys
                        or is_video_platform
                        or (template_config and template_config.type == "reels")
                    )

                    if is_video_content:
                        context.template_data["video_background"] = selected_image
                    else:
                        context.template_data["main_image"] = selected_image

            self.state_manager.update_context(client_id, context.model_dump())

            # Confirm the selection
            await self.send_message(
                client_id, f"Great! You've selected image {selection_num}."
            )

            # Move to scheduling
            self.state_manager.set_state(client_id, WorkflowState.SCHEDULE_SELECTION)
            await self.send_scheduling_options(client_id)

        except ValueError as e:
            self.logger.error(f"Error parsing image selection: {e}")
            await self.send_message(
                client_id,
                "Please reply with just the number of the image you want to use (1-4).",
            )
            return

    async def handle_video_selection(self, client_id: str, message: str) -> None:
        """Handle video selection from the options presented to the user"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if we have video URLs in the context
        if not context.video_urls or len(context.video_urls) == 0:
            self.logger.error(f"No video URLs found in context for {client_id}")
            await self.send_message(
                client_id,
                "Sorry, there was an error with the video selection. Please try again.",
            )
            self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
            return

        # Try to parse the selection as a number
        try:
            # Clean up the message (remove any non-numeric characters)
            selection = "".join(filter(str.isdigit, message))
            if not selection:
                raise ValueError("No numeric selection found")

            selection_num = int(selection)

            # Check if the selection is valid
            if selection_num < 1 or selection_num > len(context.video_urls):
                await self.send_message(
                    client_id,
                    f"Please select a valid option between 1 and {len(context.video_urls)}.",
                )
                return

            # Get the selected video URL
            try:
                selected_video = context.video_urls[selection_num - 1]
                # Make sure the URL is valid
                if not selected_video or not isinstance(selected_video, str):
                    raise ValueError(f"Invalid video URL: {selected_video}")
            except (IndexError, ValueError) as e:
                self.logger.error(f"Error getting selected video: {e}")
                await self.send_message(
                    client_id,
                    "Sorry, there was an error with your selection. Please try again or upload your own video.",
                )
                self.state_manager.set_state(
                    client_id, WorkflowState.WAITING_FOR_VIDEO_UPLOAD
                )
                return

            # Store the selected video in the context
            context.selected_video = selected_video
            context.video_background = selected_video

            # Update template_data
            if not context.template_data:
                context.template_data = {}
            context.template_data["video_background"] = selected_video

            self.state_manager.update_context(client_id, context.model_dump())

            # Confirm the selection
            await self.send_message(
                client_id, f"Great! You've selected video {selection_num}."
            )

            # Move to scheduling
            self.state_manager.set_state(client_id, WorkflowState.SCHEDULE_SELECTION)
            await self.send_scheduling_options(client_id)

        except ValueError as e:
            self.logger.error(f"Error parsing video selection: {e}")
            await self.send_message(
                client_id,
                "Please reply with just the number of the video you want to use (1-4).",
            )
            return

    async def handle_waiting_for_caption(self, client_id: str, message: str) -> None:
        """Handle the WAITING_FOR_CAPTION state"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if not message:
            await self.send_message(client_id, MESSAGES["caption_prompt"])
            return

        # Extract platform and content_type from template_id
        parts = context.template_id.split("_")
        if len(parts) < 3:
            self.logger.error(f"Invalid template ID format: {context.template_id}")
            await self.send_message(
                client_id, "Sorry, there was an error processing your caption."
            )
            return

        platform = parts[0]
        content_type = parts[2]

        # Get template config to check caption type
        template_config = get_template_config(platform, content_type)
        if not template_config:
            self.logger.error(
                f"Template config not found for {platform}_{content_type}"
            )
            await self.send_message(
                client_id, "Sorry, there was an error processing your caption."
            )
            return

        # Store the caption based on template configuration
        uses_caption_text = "caption_text" in template_config.fields
        uses_post_caption = "post_caption" in template_config.fields

        # Store the caption in appropriate fields
        if uses_caption_text:
            context.caption = message
            if not context.template_data:
                context.template_data = {}
            context.template_data["caption_text"] = message
        elif uses_post_caption:
            context.post_caption = message
            context.caption = message  # For compatibility
        else:
            context.caption = message

        context.original_text = message
        self.state_manager.update_context(client_id, context.model_dump())

        # Generate content based on the caption
        await self.send_message(client_id, MESSAGES["generating"])

        try:
            # Prepare user inputs for template
            user_inputs = {
                "destination_name": context.destination_name,  # Add destination name to user inputs
            }

            if uses_caption_text:
                user_inputs["caption_text"] = message
            elif uses_post_caption:
                user_inputs["post_caption"] = message

            # Add any existing media to user_inputs
            if context.selected_image:
                user_inputs["main_image"] = context.selected_image
            if context.selected_video:
                user_inputs["video_background"] = context.selected_video

            # Generate content using template
            (
                caption,
                media_urls,
                template_data,
            ) = await self.content_generator.generate_template_content(
                template_id=context.template_id, user_inputs=user_inputs
            )

            # Store the appropriate caption
            if uses_post_caption:
                context.post_caption = caption
                context.caption = caption  # For compatibility
            else:
                context.caption = caption
                # For templates that use caption_text, also store in template_data
                if uses_caption_text and not template_data.get("caption_text"):
                    template_data["caption_text"] = caption

            # Store media URLs and update context before asking for image upload
            if media_urls and len(media_urls) > 0:
                context.image_urls = media_urls
                if template_data and "media_options" not in template_data:
                    template_data["media_options"] = media_urls

            context.template_data = template_data
            self.state_manager.update_context(client_id, context.model_dump())

            # Send the generated caption
            caption_to_show = (
                context.post_caption if context.post_caption else context.caption
            )
            await self.send_message(
                client_id, f"Here is the caption for the post: {caption_to_show}"
            )

            # Check if we already have media
            if context.selected_image or context.selected_video:
                # Move directly to scheduling if we already have media
                self.state_manager.set_state(
                    client_id, WorkflowState.SCHEDULE_SELECTION
                )
                await self.send_scheduling_options(client_id)
            else:
                # Ask for media upload if needed
                await self.ask_for_media_upload(client_id)

        except Exception as e:
            self.logger.error(f"Error generating content: {e}")
            await self.send_message(client_id, f"Error generating content: {e}")
            # Reset to caption input state
            self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)

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

    async def handle_waiting_for_tip_details(
        self, client_id: str, message: str
    ) -> None:
        """Handle tip details input"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if this is a media message
        context_data = self.state_manager.get_context(client_id)
        if context_data.get("is_media_message", False) or message.startswith(
            "MEDIA_MESSAGE:"
        ):
            # This is a media message, not tip details
            await self.send_message(
                client_id,
                "I need text for your tip details, not a media file. Please provide additional details for your tip:",
            )
            return

        # Store the tip details
        context.tip_details = message
        self.state_manager.update_context(client_id, context.model_dump())

        await self.send_message(client_id, "Great! Tip details saved.")

        # Return to caption input state and continue processing
        self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
        await self.handle(client_id, context.original_text)

    async def handle_waiting_for_seasonal_details(
        self, client_id: str, message: str
    ) -> None:
        """Handle seasonal details input"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if this is a media message
        context_data = self.state_manager.get_context(client_id)
        if context_data.get("is_media_message", False) or message.startswith(
            "MEDIA_MESSAGE:"
        ):
            # This is a media message, not seasonal details
            await self.send_message(
                client_id,
                "I need text for your seasonal details, not a media file. Please provide additional details about this seasonal post:",
            )
            return

        # Store the seasonal details
        context.seasonal_details = message
        self.state_manager.update_context(client_id, context.model_dump())

        await self.send_message(client_id, "Great! Seasonal details saved.")

        # Return to caption input state and continue processing
        self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
        await self.handle(client_id, context.original_text)
