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
            self.logger.info(f"Generating images for: {promo_text_search}")
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
            Tuple of (caption, image_urls, template_data)
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

            self.logger.info(
                f"Generating content for template {template_id} of type {template_type}"
            )

            # Initialize result dict with template info
            template_data = {
                "template_id": template_id,
                "template_type": template_type,
                "required_keys": required_keys,
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

            # Generate image search query based on template type and context
            search_query = await self.openai_service.generate_image_search_query(
                template_type=template_type, context=context
            )

            if not search_query:
                search_query = user_inputs.get(
                    "destination_name", user_inputs.get("event_name", template_type)
                )

            # Search for images based on required media types
            image_urls = []
            if "main_image" in required_keys or "event_image" in required_keys:
                self.logger.info(f"Searching images with query: {search_query}")
                image_urls = await self.image_service.search_images(
                    search_query, limit=4
                )

                if not image_urls:
                    self.logger.warning(
                        f"No images found for {search_query}, using default"
                    )
                    image_urls = ["https://example.com/mock-image.jpg"] * 4

            # Add video background if needed
            if "video_background" in required_keys:
                # For video-based templates, we'd typically need different search terms
                video_search = f"{search_query} video background"
                self.logger.info(
                    f"Searching video backgrounds with query: {video_search}"
                )
                # In a real implementation, we would search for videos
                # For now, we'll use the image_service but this would be replaced
                template_data["video_background"] = "https://example.com/mock-video.mp4"

            # Create full template data with all required fields
            for key in required_keys:
                if key == "main_image" and image_urls:
                    template_data[key] = image_urls[0]
                elif key == "event_image" and "event_image" in user_inputs:
                    # User-uploaded event images should be used as-is
                    template_data[key] = user_inputs.get("event_image")
                elif key == "caption_text" and caption:
                    template_data[key] = caption
                elif key in user_inputs:
                    template_data[key] = user_inputs[key]

            return caption, image_urls, template_data

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
