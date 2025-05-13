from typing import Tuple, List, Dict, Any, Optional
from app.services.common.logging import setup_logger
from .openai_service import AsyncOpenAIService
from .image_service import ImageService
from app.constants import OPENAI_PROMPTS, TEMPLATE_CONFIG


class ContentGenerator:
    """Service for generating content"""

    def __init__(self):
        self.openai_service = AsyncOpenAIService()
        self.image_service = ImageService()
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
            image_results = await self.image_service.search_images(
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
        """
        Generate content based on a specific template from TEMPLATE_CONFIG.

        Args:
            template_id: The ID of the template to use
            user_inputs: Dictionary containing user-provided inputs like destination_name

        Returns:
            Tuple of (caption, media_urls, template_data)
        """
        try:
            # Get template details from TEMPLATE_CONFIG
            template_details = TEMPLATE_CONFIG["templates"].get(template_id)
            if not template_details:
                self.logger.error(
                    f"Template {template_id} not found in TEMPLATE_CONFIG"
                )
                raise ValueError(f"Template {template_id} not found")

            template_type = template_details.get("type", "generic")
            required_keys = template_details.get("required_keys", [])

            # Check if this is a platform that requires video (like TikTok)
            platform = template_id.split("_")[0] if "_" in template_id else ""
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
                media_urls = await self.image_service.search_images(
                    search_query, limit=4
                )

                if not media_urls:
                    self.logger.warning(
                        f"No images found for {search_query}, using default"
                    )
                    media_urls = ["https://example.com/mock-image.jpg"] * 4

                # Set main_image in template data
                if media_urls:
                    template_data["main_image"] = media_urls[0]

            # Handle video content
            elif is_video_content:
                # In a real implementation, we would have a video service similar to image_service
                # For now, we'll use mock video URLs
                self.logger.info(f"Searching for video with query: {search_query}")

                # Mock video URLs - in a real implementation, this would call a video API
                media_urls = [
                    "https://example.com/mock-video1.mp4",
                    "https://example.com/mock-video2.mp4",
                    "https://example.com/mock-video3.mp4",
                    "https://example.com/mock-video4.mp4",
                ]

                # Set video_background in template data
                if media_urls:
                    template_data["video_background"] = media_urls[0]

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
        """
        Find a template ID based on platform, content type and client ID.

        Args:
            platform: The social media platform (instagram, linkedin, tiktok)
            content_type: The type of content (destination, events, etc.)
            client_id: The client's ID

        Returns:
            Template ID if found, None otherwise
        """
        try:
            # Create the template ID pattern
            template_pattern = f"{platform}_{client_id}_{content_type}"

            # Look for exact match
            if template_pattern in TEMPLATE_CONFIG["templates"]:
                return template_pattern

            # Look for matching templates by type
            for template_id, details in TEMPLATE_CONFIG["templates"].items():
                if (
                    template_id.startswith(f"{platform}_")
                    and template_id.endswith(f"_{content_type}")
                    and details["type"] == content_type
                ):
                    return template_id

            # Fallback to any template of matching type
            for template_id, details in TEMPLATE_CONFIG["templates"].items():
                if details["type"] == content_type:
                    self.logger.warning(
                        f"Using fallback template {template_id} for {platform}_{content_type}"
                    )
                    return template_id

            return None
        except Exception as e:
            self.logger.error(f"Error finding template: {e}")
            return None
