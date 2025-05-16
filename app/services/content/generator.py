from typing import Tuple, List, Dict, Any, Optional
from app.services.common.logging import setup_logger
from .openai_service import AsyncOpenAIService
from .image_service import MediaService
from app.constants import OPENAI_PROMPTS
from app.services.content.template_service import template_service
from app.services.content.template_config import get_template_config


class ContentGenerator:
    """Service for generating content"""

    def __init__(self):
        self.openai_service = AsyncOpenAIService()
        self.media_service = MediaService()
        self.logger = setup_logger(__name__)

    async def generate_content(self, promo_text: str) -> Tuple[str, List[str]]:
        """Generate engaging content for a given promotional text."""
        try:
            # Generate caption using OpenAI
            caption = await self.openai_service.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": OPENAI_PROMPTS["caption_system"],
                    },
                    {
                        "role": "user",
                        "content": OPENAI_PROMPTS["caption_user"].format(
                            promo_text=promo_text
                        ),
                    },
                ]
            )
            if not caption:
                self.logger.warning("No caption generated, using default.")
                caption = f"✨ {promo_text}\n\n#trending #viral #marketing"

            # Find relevant images
            promo_text_search = await self.openai_service.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": OPENAI_PROMPTS["search_system"],
                    },
                    {
                        "role": "user",
                        "content": OPENAI_PROMPTS["search_user"].format(
                            caption=caption
                        ),
                    },
                ]
            )
            if not promo_text_search:
                self.logger.warning("No search query generated, using default.")
                promo_text_search = promo_text

            # Search for images
            self.logger.info(f"Fetching images with query: {promo_text_search}")
            image_results = await self.media_service.search_images(
                promo_text_search, limit=4
            )
            if not image_results or len(image_results) < 4:
                self.logger.warning("Not enough images found, using default.")
                image_results = ["https://example.com/mock-image.jpg"] * 4
                return caption, image_results
            return caption, image_results

        except Exception as e:
            self.logger.error(f"Error generating content: {e}")
            return (
                "Error generating content",
                ["https://example.com/mock-image.jpg"] * 4,
            )

    async def generate_template_content(
        self, template_id: str, user_inputs: Dict[str, Any]
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """Generate content based on a specific template."""

        try:
            # Extract platform and content_type from template_id
            parts = template_id.split("_")
            if len(parts) < 3:
                self.logger.error(f"Invalid template ID format: {template_id}")
                raise ValueError(f"Invalid template ID format: {template_id}")

            platform = parts[0]
            content_type = parts[2]

            # Get template details using the template service
            template_config = get_template_config(platform, content_type)
            if not template_config:
                self.logger.error(
                    f"Template config not found for {platform}_{content_type}"
                )
                raise ValueError(
                    f"Template config not found for {platform}_{content_type}"
                )

            template_type = template_config.type
            required_keys = template_service.get_required_fields(platform, content_type)

            # Check if this is a platform that requires video (like TikTok)
            is_video_platform = platform.lower() == "tiktok"

            # Determine if this is a video-based template
            is_video_content = (
                "video_background" in required_keys
                or is_video_platform
                or template_type == "reels"
            )

            self.logger.info(
                f"Generating content for template {template_id} of type {template_type} (video content: {is_video_content})"
            )

            # Initialize result dict with template info
            template_data = {
                "template_id": template_id,
                "template_type": template_type,
                "required_keys": required_keys,
                "is_video_content": is_video_content,
            }

            # Validate and process user inputs for required fields
            for key in required_keys:
                if key.endswith("_name") and key in user_inputs:
                    # Validate name inputs (e.g., destination_name, event_name)
                    is_valid, result = self.openai_service.validate_user_input(
                        user_inputs.get(key, ""), max_words=5
                    )
                    if not is_valid:
                        self.logger.warning(f"Invalid input for {key}: {result}")
                        raise ValueError(result)
                    user_inputs[key] = result

            # Generate caption based on template type
            context = user_inputs.copy()
            caption = await self.openai_service.generate_formatted_caption(
                template_type=template_type, context=context, use_emojis=True
            )

            if not caption:
                self.logger.warning(
                    f"No caption generated for {template_id}, using fallback"
                )
                caption = (
                    f"✨ Check out our {template_type} content! #trending #marketing"
                )

            # Add caption to context and template data
            context["caption"] = caption
            template_data["caption_text"] = caption

            # Generate appropriate search query based on template type and context
            if is_video_content:
                search_query = f"{template_type} background video"
                if template_type == "destination" and "destination_name" in context:
                    search_query = (
                        f"{context['destination_name']} travel video background"
                    )
                elif template_type == "reels":
                    search_query = "dynamic background video"
            else:
                search_query = await self.openai_service.generate_image_search_query(
                    template_type=template_type, context=context
                )

            if not search_query:
                search_query = user_inputs.get(
                    "destination_name", user_inputs.get("event_name", template_type)
                )

            # Initialize media URLs list
            media_urls = []

            # Handle event_image if provided (client upload)
            if "event_image" in required_keys and "event_image" in user_inputs:
                # Use the uploaded event image directly
                event_image = user_inputs.get("event_image")
                if event_image:
                    media_urls = [event_image]
                    template_data["event_image"] = event_image

            # Handle media search based on required_keys and content type
            elif "main_image" in required_keys and not is_video_content:
                # Search for images
                self.logger.info(f"Searching images with query: {search_query}")
                media_urls = await self.media_service.search_images(
                    search_query, limit=4
                )

                if not media_urls:
                    self.logger.warning(
                        f"No images found for {search_query}, using default"
                    )
                    media_urls = ["https://example.com/mock-image.jpg"] * 4

                # Store all media URLs in template data for selection
                if media_urls:
                    # We'll let the user select which image to use
                    template_data["media_options"] = media_urls

            # Handle video content
            elif is_video_content:
                # Search for videos using our VideoService
                self.logger.info(f"Searching for videos with query: {search_query}")
                media_urls = await self.media_service.search_videos(
                    search_query, limit=4
                )

                if not media_urls:
                    self.logger.warning(
                        f"No videos found for {search_query}, using default"
                    )
                    # Fallback to mock video URLs
                    media_urls = [
                        "https://example.com/mock-video1.mp4",
                        "https://example.com/mock-video2.mp4",
                        "https://example.com/mock-video3.mp4",
                        "https://example.com/mock-video4.mp4",
                    ]

                # Store all video URLs in template data for selection
                if media_urls:
                    # We'll let the user select which video to use
                    template_data["media_options"] = media_urls

            # Create full template data with all required fields
            for key in required_keys:
                if key not in template_data and key in user_inputs:
                    template_data[key] = user_inputs[key]

            return caption, media_urls, template_data

        except ValueError as ve:
            # Re-raise validation errors
            self.logger.error(f"Validation error: {ve}")
            raise
        except Exception as e:
            self.logger.error(f"Error generating template content: {e}")
            return (
                "Error generating content",
                ["https://example.com/mock-image.jpg"] * 4,
                {"error": str(e)},
            )

    def get_template_by_platform_and_type(
        self, platform: str, content_type: str, client_id: str
    ) -> Optional[str]:
        """Find a template ID based on platform, content type and client ID."""

        try:
            # Use the template service to get the template ID
            return template_service.get_template_id(platform, content_type, client_id)
        except Exception as e:
            self.logger.error(f"Error finding template: {e}")
            return None
