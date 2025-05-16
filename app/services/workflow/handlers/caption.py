from typing import List
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
from app.services.common.types import WorkflowContext, MediaItem
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
                    if "event_image" in get_required_keys(
                        context.template_id
                    ):
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
        await self.ask_for_image_upload(client_id)

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

            # Use the template service to get the next field to collect
            next_field = template_service.get_next_field_to_collect(
                platform=platform, content_type=content_type, context=context
            )

            if next_field:
                field_name, workflow_state, prompt = next_field
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
                client_id, f"Here is the caption for the post: {context.caption}"
            )

            # Check if we need to ask for image upload or use external service
            await self.ask_for_image_upload(client_id)

        except Exception as e:
            self.logger.error(f"Error generating content: {e}")
            await self.send_message(client_id, f"Error generating content: {e}")
            # Reset to caption input state
            self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)

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

    async def handle_media_upload(self, client_id: str, message: str) -> None:
        """Handle image upload from WhatsApp"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if this is a structured media message
        if message.startswith("MEDIA_MESSAGE:"):
            parts = message.split(":")
            if len(parts) >= 3:
                media_type = parts[1]
                media_id = parts[2]

                self.logger.info(f"Processing {media_type} upload with ID: {media_id}")

                # Check if we already have a URL from the workflow manager
                # First check in the WorkflowContext object
                public_url = None

                # Then check in the raw context dictionary
                context_dict = self.state_manager.get_context(client_id)
                if "media_url" in context_dict:
                    public_url = context_dict["media_url"]
                    self.logger.info(
                        f"Using media URL from context: {public_url[:50]}..."
                    )

                # If not, try to download it now
                if not public_url:
                    public_url = await save_whatsapp_image(media_id, client_id)

                if public_url:
                    # Store the public URL in the context
                    context.selected_image = public_url

                    # Also set event_image if needed by template
                    if context.template_id:
                        parts = context.template_id.split("_")
                        if len(parts) >= 3:
                            content_type = parts[2]

                            # For events templates, set main_image
                            if content_type == "events":
                                self.logger.info(
                                    f"Setting main_image for events template to {public_url[:50]}..."
                                )
                                if not context.template_data:
                                    context.template_data = {}
                                context.template_data["main_image"] = public_url

                            # For templates requiring event_image
                            if "event_image" in get_required_keys(
                                context.template_id
                            ):
                                context.event_image = public_url
                                self.logger.info(
                                    "Also setting event_image to the same URL for template compatibility"
                                )

                                # Update template data if it exists
                                if context.template_data:
                                    context.template_data["event_image"] = public_url

                    self.state_manager.update_context(client_id, context.model_dump())
                    await self.send_message(client_id, "Image uploaded successfully!")

                    # Move to scheduling
                    self.state_manager.set_state(
                        client_id, WorkflowState.SCHEDULE_SELECTION
                    )
                    await self.send_scheduling_options(client_id)
                else:
                    # Failed to download media
                    await self.send_message(
                        client_id,
                        f"I couldn't process your {media_type}. Please upload it again.",
                    )
            else:
                # Invalid format
                await self.send_message(
                    client_id,
                    "Invalid media message format. Please upload your image again.",
                )
        # For backward compatibility, handle the old format
        elif message.startswith("Received image with ID:") or message.startswith(
            "Received media with ID:"
        ):
            # Extract media ID from the message
            media_id = message.split("ID:")[-1].strip()
            self.logger.info(
                f"Processing image upload with ID: {media_id} (legacy format)"
            )

            # Download and get public URL in one step
            public_url = await save_whatsapp_image(media_id, client_id)

            if public_url:
                context.selected_image = public_url

                # Also set event_image if needed by template
                if context.template_id:
                    parts = context.template_id.split("_")
                    if len(parts) >= 3:
                        content_type = parts[2]

                        # For events templates, set main_image
                        if content_type == "events":
                            self.logger.info(
                                f"Setting main_image for events template to {public_url[:50]}..."
                            )
                            if not context.template_data:
                                context.template_data = {}
                            context.template_data["main_image"] = public_url

                        # For templates requiring event_image
                        if "event_image" in get_required_keys(
                            context.template_id
                        ):
                            context.event_image = public_url
                            self.logger.info(
                                "Also setting event_image to the same URL for template compatibility"
                            )

                            # Update template data if it exists
                            if context.template_data:
                                context.template_data["event_image"] = public_url

                self.state_manager.update_context(client_id, context.model_dump())
                await self.send_message(client_id, "Image uploaded successfully!")

                # Move to scheduling
                self.state_manager.set_state(
                    client_id, WorkflowState.SCHEDULE_SELECTION
                )
                await self.send_scheduling_options(client_id)
            else:
                # Failed to download media
                await self.send_message(
                    client_id, "I couldn't process your image. Please upload it again."
                )
        elif message.startswith("http") and ("://" in message):
            # For direct URLs, just store the URL (we don't support this anymore)
            await self.send_message(
                client_id,
                "Please upload an image directly through WhatsApp instead of sending a URL.",
            )
        # Handle the case where the message is already a media URL path from our server
        elif message.startswith("/media/images/") and message.endswith(
            (".jpg", ".jpeg", ".png")
        ):
            # This is already a processed media URL, use it directly
            self.logger.info(f"Using already processed media URL: {message}")

            # Store the public URL in the context
            context.selected_image = message

            # Also set event_image if needed by template
            if context.template_id:
                parts = context.template_id.split("_")
                if len(parts) >= 3:
                    content_type = parts[2]

                    # For events templates, set main_image
                    if content_type == "events":
                        self.logger.info(
                            f"Setting main_image for events template to {message[:50]}..."
                        )
                        if not context.template_data:
                            context.template_data = {}
                        context.template_data["main_image"] = message

                    # For templates requiring event_image
                    if "event_image" in get_required_keys(
                        context.template_id
                    ):
                        context.event_image = message
                        self.logger.info(
                            "Also setting event_image to the same URL for template compatibility"
                        )

                        # Update template data if it exists
                        if context.template_data:
                            context.template_data["event_image"] = message

            self.state_manager.update_context(client_id, context.model_dump())
            await self.send_message(client_id, "Image uploaded successfully!")

            # Move to scheduling
            self.state_manager.set_state(client_id, WorkflowState.SCHEDULE_SELECTION)
            await self.send_scheduling_options(client_id)
        else:
            # Invalid format
            await self.send_message(
                client_id,
                "Please send your image as an attachment.",
            )

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
