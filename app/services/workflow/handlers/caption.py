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
        elif current_state == WorkflowState.WAITING_FOR_HEADLINE:
            await self.handle_headline_input(client_id, message)
            return
        elif current_state == WorkflowState.WAITING_FOR_TIP_DETAILS:
            await self.handle_waiting_for_tip_details(client_id, message)
            return
        elif current_state == WorkflowState.WAITING_FOR_SEASONAL_DETAILS:
            await self.handle_waiting_for_seasonal_details(client_id, message)
            return

        if not message:
            # Check if we need to collect template-specific fields first
            if context.template_id:
                if await self.request_template_fields(client_id):
                    return  # Waiting for additional input

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

                    # If we already have a selected_image and template needs event_image, set it
                    if (
                        "event_image" in get_required_keys(template_id)
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
                # Extract platform and content_type from template_id
                parts = context.template_id.split("_")
                platform = parts[0] if len(parts) >= 1 else ""
                content_type = parts[2] if len(parts) >= 3 else ""

                # Prepare user inputs for template
                user_inputs = {}

                # For seasonal templates, use the headline as caption_text
                if content_type == "seasonal" and context.caption:
                    user_inputs["caption_text"] = context.caption
                else:
                    user_inputs["caption_text"] = message

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
                    if "event_image" in get_required_keys(context.template_id):
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

                # Make sure we store the media URLs properly
                if media_urls and len(media_urls) > 0:
                    self.logger.info(f"Storing {len(media_urls)} media URLs in context")
                    context.image_urls = media_urls
                    context.selected_image = media_urls[0]

                    # Also store media options in template_data if not already there
                    if template_data and "media_options" not in template_data:
                        template_data["media_options"] = media_urls

                context.template_data = template_data

                # CRITICAL: Update the state manager with the modified context
                self.state_manager.update_context(client_id, context.model_dump())

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

            # Make sure we store the image URLs properly
            if image_urls and len(image_urls) > 0:
                self.logger.info(
                    f"Storing {len(image_urls)} fallback media URLs in context"
                )
                context.image_urls = image_urls
                context.selected_image = image_urls[0]

            # CRITICAL: Update the state manager with the modified context
            self.state_manager.update_context(client_id, context.model_dump())

        # Send the generated caption
        await self.send_message(
            client_id, f"Here is the caption for the post: {context.caption}"
        )

        # Double-check that context is properly saved before proceeding
        raw_context = self.state_manager.get_context(client_id)
        if "image_urls" not in raw_context or not raw_context["image_urls"]:
            self.logger.warning(
                "image_urls missing from context before ask_for_image_upload, re-saving context"
            )
            self.state_manager.update_context(client_id, context.model_dump())

        # Ask for image upload
        await self.ask_for_media_upload(client_id)

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

        # Return to caption input state and continue processing
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
        """Ask the user to upload media based on template configuration"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if context.template_id:
            # Extract platform and content_type from template_id
            parts = context.template_id.split("_")
            if len(parts) >= 3:
                platform = parts[0]
                content_type = parts[2]
                template_config = get_template_config(platform, content_type)

                if template_config and template_config.is_video:
                    # For video content from external service
                    if "video_background" in template_config.fields:
                        field_config = template_config.fields["video_background"]
                        if field_config.source == FieldSource.EXTERNAL_SERVICE:
                            await self.send_message(
                                client_id,
                                field_config.prompt
                                or "We'll find a suitable video for your post.",
                            )
                            # Search for videos using the content type as query
                            search_query = content_type
                            if context.caption:
                                search_query = context.caption

                            try:
                                # Use the media service to search for videos
                                video_urls = await self.media_service.search_videos(
                                    search_query, limit=4
                                )

                                if video_urls:
                                    context.video_urls = video_urls
                                    self.state_manager.update_context(
                                        client_id, context.model_dump()
                                    )

                                    # Send videos to user for selection
                                    for i, video_url in enumerate(video_urls, 1):
                                        await self.client.send_media(
                                            media_items=[
                                                {"type": "video", "url": video_url}
                                            ],
                                            phone_number=client_id,
                                        )
                                        await self.send_message(
                                            client_id, f"Video option {i}"
                                        )

                                    # Update state and ask for selection
                                    self.state_manager.set_state(
                                        client_id, WorkflowState.VIDEO_SELECTION
                                    )
                                    await self.send_message(
                                        client_id,
                                        "Please reply with the number of the video you want to use (1-4).",
                                    )
                                    return
                                else:
                                    self.logger.warning(
                                        f"No videos found for query: {search_query}"
                                    )
                                    await self.send_message(
                                        client_id,
                                        "We couldn't find suitable videos. Please upload your own video.",
                                    )
                                    self.state_manager.set_state(
                                        client_id,
                                        WorkflowState.WAITING_FOR_VIDEO_UPLOAD,
                                    )
                                    return
                            except Exception as e:
                                self.logger.error(f"Error searching for videos: {e}")
                                await self.send_message(
                                    client_id,
                                    "We encountered an error finding videos. Please upload your own video.",
                                )
                                self.state_manager.set_state(
                                    client_id, WorkflowState.WAITING_FOR_VIDEO_UPLOAD
                                )
                                return

        # For non-video content or if no specific template config found
        if context.is_video_content:
            await self.send_message(
                client_id,
                "Please upload a video for your post. The video should be in MP4 format and less than 60 seconds.",
            )
            self.state_manager.set_state(
                client_id, WorkflowState.WAITING_FOR_VIDEO_UPLOAD
            )
        else:
            # For image content, proceed with existing image upload flow
            await self.ask_for_image_upload(client_id)

    async def handle_media_upload(self, client_id: str, message: str) -> None:
        """Handle media upload from WhatsApp"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        try:
            # Extract media ID and type from message
            media_id = message.split(":")[2]
            media_type = message.split(":")[1]

            if context.is_video_content and media_type != "video":
                await self.send_message(
                    client_id,
                    "This post requires a video. Please upload a video file in MP4 format.",
                )
                return

            elif not context.is_video_content and media_type != "image":
                await self.send_message(
                    client_id,
                    "This post requires an image. Please upload an image file.",
                )
                return

            # Process the media upload
            public_url = await self._process_media_upload(
                client_id, media_id, media_type
            )

            if public_url:
                if context.is_video_content:
                    context.selected_video = public_url
                    context.video_background = public_url
                    if context.template_data is None:
                        context.template_data = {}
                    context.template_data["video_background"] = public_url
                else:
                    context.selected_image = public_url
                    if context.template_data is None:
                        context.template_data = {}
                    context.template_data["main_image"] = public_url

                self.state_manager.update_context(client_id, context.model_dump())
                await self.send_message(client_id, "Media uploaded successfully!")

                # Move to scheduling
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

    async def ask_for_image_upload(self, client_id: str) -> None:
        """Ask the user to upload an image or search for one based on template configuration"""
        # Get the raw context first for debugging
        raw_context = self.state_manager.get_context(client_id)
        self.logger.info(
            f"Raw context for {client_id}: image_urls present: {'image_urls' in raw_context}"
        )
        if "image_urls" in raw_context:
            self.logger.info(
                f"Raw context image_urls length: {len(raw_context['image_urls'])}"
            )

        # Ensure caption field is present with at least an empty string
        if "caption" not in raw_context or raw_context["caption"] is None:
            raw_context["caption"] = ""

        # Convert to WorkflowContext object
        context = WorkflowContext(**raw_context)

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

                        # If we have image URLs from content generation, show them for selection
                        if context.image_urls and len(context.image_urls) > 0:
                            self.logger.info(
                                f"Found {len(context.image_urls)} images in context for {client_id}"
                            )

                            # Show up to 4 images for selection
                            max_images = min(4, len(context.image_urls))
                            self.logger.info(
                                f"Showing {max_images} images for selection"
                            )

                            # Send each image as a separate message
                            for i in range(max_images):
                                image_url = context.image_urls[i]
                                self.logger.info(
                                    f"Sending image {i + 1}: {image_url[:50]}..."
                                )
                                # Send the image with a number for selection
                                await self.client.send_media(
                                    {
                                        "type": "image",
                                        "url": image_url,
                                        "caption": f"Option {i + 1}",
                                    },
                                    client_id,
                                )

                            # Update context to indicate we're waiting for image selection
                            self.state_manager.set_state(
                                client_id, WorkflowState.IMAGE_SELECTION
                            )

                            # Send a message asking to select an image
                            await self.send_message(
                                client_id,
                                "Please reply with the number of the image you want to use (1-4).",
                            )
                            return
                        else:
                            # No images found, try a more generic search
                            self.logger.warning(
                                f"No images found in context.image_urls for {client_id}, trying generic search"
                            )

                            # Log template data to help diagnose issues
                            if (
                                context.template_data
                                and "media_options" in context.template_data
                            ):
                                self.logger.info(
                                    f"Found {len(context.template_data['media_options'])} images in template_data.media_options"
                                )
                                # Use these images instead
                                context.image_urls = context.template_data[
                                    "media_options"
                                ]
                                self.state_manager.update_context(
                                    client_id, context.model_dump()
                                )

                                # Recursively call this method again to show the images
                                await self.ask_for_image_upload(client_id)
                                return

                            # Try to get the content type for a more generic search
                            generic_search_term = (
                                content_type  # Default to content type
                            )

                            # For destination templates, use more specific search terms
                            if content_type == "destination":
                                # If we have a destination name, use it for a more specific search
                                if context.destination_name:
                                    generic_search_term = f"{context.destination_name} travel destination scenic"
                                else:
                                    generic_search_term = (
                                        "scenic travel destination landscape"
                                    )
                            # For seasonal templates, use "seasonal"
                            elif content_type == "seasonal":
                                generic_search_term = "seasonal celebration holiday"
                            # For event templates, use "event"
                            elif content_type == "event":
                                if context.event_name:
                                    generic_search_term = f"{context.event_name} event"
                                else:
                                    generic_search_term = "special event celebration"

                            # Generate generic images
                            self.logger.info(
                                f"Searching for generic images with query: {generic_search_term}"
                            )

                            # Use the content generator to search for images
                            try:
                                generic_images = await self.content_generator.media_service.search_images(
                                    generic_search_term, limit=4
                                )

                                if generic_images and len(generic_images) > 0:
                                    # Store the generic images in the context
                                    context.image_urls = generic_images
                                    self.state_manager.update_context(
                                        client_id, context.model_dump()
                                    )

                                    # Show the generic images for selection
                                    await self.send_message(
                                        client_id,
                                        f"We couldn't find specific images for '{platform}_{content_type}'. Here are some general options:",
                                    )

                                    # Show up to 4 images for selection
                                    max_images = min(4, len(generic_images))

                                    # Send each image as a separate message
                                    for i in range(max_images):
                                        image_url = generic_images[i]
                                        # Send the image with a number for selection
                                        await self.client.send_media(
                                            {
                                                "type": "image",
                                                "url": image_url,
                                                "caption": f"Option {i + 1}",
                                            },
                                            client_id,
                                        )

                                    # Update context to indicate we're waiting for image selection
                                    self.state_manager.set_state(
                                        client_id, WorkflowState.IMAGE_SELECTION
                                    )

                                    # Send a message asking to select an image
                                    await self.send_message(
                                        client_id,
                                        "Please reply with the number of the image you want to use (1-4).",
                                    )
                                    return
                            except Exception as e:
                                self.logger.error(
                                    f"Error searching for generic images: {e}"
                                )

                            # If we get here, we couldn't find any images, ask for upload
                            self.state_manager.set_state(
                                client_id, WorkflowState.WAITING_FOR_MEDIA_UPLOAD
                            )
                            await self.send_message(
                                client_id,
                                "We couldn't find suitable images. Please upload an image for your post.",
                            )
                            return

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

        # Store the caption if not already stored
        if not context.caption:
            context.caption = message
            context.original_text = message
            self.state_manager.update_context(client_id, context.model_dump())

            # Initialize template_data if not exists
            if not context.template_data:
                context.template_data = {}
            context.template_data["caption_text"] = message
            self.state_manager.update_context(client_id, context.model_dump())

        # Generate content based on the caption
        await self.send_message(client_id, MESSAGES["generating"])

        try:
            # Prepare user inputs for template
            user_inputs = {
                "caption_text": context.caption,  # Use stored caption
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
                self.logger.info(f"Storing {len(media_urls)} media URLs in context")
                context.image_urls = media_urls
                context.selected_image = media_urls[0]

                # Also store media options in template_data if not already there
                if template_data and "media_options" not in template_data:
                    template_data["media_options"] = media_urls

            context.template_data = template_data
            self.state_manager.update_context(client_id, context.model_dump())

            # Send the generated caption
            await self.send_message(
                client_id, f"Here is the caption for the post: {context.caption}"
            )

            # Move to media upload/selection
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
