from typing import Tuple, List, Dict, Any, Optional
from app.logging import setup_logger
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
        self.default_image = "https://example.com/mock-image.jpg"
        self.default_video = "https://example.com/mock-video.mp4"

    async def generate_content(self, promo_text: str) -> Tuple[str, List[str]]:
        """Generate engaging content for a given promotional text."""
        try:
            # Generate caption
            caption = await self._generate_with_openai(
                OPENAI_PROMPTS["caption_system"],
                OPENAI_PROMPTS["caption_user"],
                promo_text=promo_text,
            )
            if not caption:
                caption = f"✨ {promo_text}"

            # Generate search query
            search_query = await self._generate_with_openai(
                OPENAI_PROMPTS["search_system"],
                OPENAI_PROMPTS["search_user"],
                caption=caption,
            )
            if not search_query:
                search_query = promo_text

            # Get media URLs
            image_results = await self._get_media_urls(search_query)
            if not image_results:
                image_results = [self.default_image] * 4

            return caption, image_results

        except Exception as e:
            self.logger.error(f"Error generating content: {e}")
            return "Error generating content", [self.default_image] * 4

    async def generate_template_content(
        self, template_id: str, user_inputs: Dict[str, Any]
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """Generate content based on a specific template."""
        try:
            # Validate template ID
            parts = template_id.split("_")
            if len(parts) < 3:
                raise ValueError(f"Invalid template ID format: {template_id}")

            # Get template config
            platform, content_type = parts[0], parts[2]
            template_config = get_template_config(platform, content_type)
            if not template_config:
                raise ValueError(
                    f"Template config not found for {platform}_{content_type}"
                )

            # Get template details
            required_keys = [
                key for key, field in template_config.fields.items() if field.required
            ]
            template_type = template_config.type
            is_video_content = template_type == "video"

            # Generate caption
            context = {**user_inputs, "template_type": template_type}

            # Check if this template uses post_caption instead of caption_text
            uses_post_caption = "post_caption" in template_config.fields
            caption_field = "post_caption" if uses_post_caption else "caption_text"

            caption = await self.openai_service.generate_formatted_caption(
                template_type=template_type,
                context=context,
                caption_field=caption_field,
            )

            # Handle media
            search_query = user_inputs.get(
                "destination_name", user_inputs.get("event_name", template_type)
            )
            media_urls = []
            template_data = {}

            # Add the generated caption to template data
            if caption:
                template_data[caption_field] = caption

            if "event_image" in required_keys and user_inputs.get("event_image"):
                media_urls = [user_inputs["event_image"]]
                template_data["event_image"] = user_inputs["event_image"]
            elif "main_image" in required_keys and not is_video_content:
                media_urls = (
                    await self._get_media_urls(search_query) or [self.default_image] * 4
                )
                template_data["media_options"] = media_urls
            elif is_video_content:
                media_urls = (
                    await self._get_media_urls(search_query, is_video=True)
                    or [self.default_video] * 4
                )
                template_data["media_options"] = media_urls

            # Populate template data
            for key in required_keys:
                if key not in template_data and key in user_inputs:
                    template_data[key] = user_inputs[key]

            return caption, media_urls, template_data

        except ValueError as ve:
            self.logger.error(f"Validation error: {ve}")
            raise
        except Exception as e:
            self.logger.error(f"Error generating template content: {e}")
            return (
                "Error generating content",
                [self.default_image] * 4,
                {"error": str(e)},
            )

    def get_template_by_platform_and_type(
        self, platform: str, content_type: str, client_id: str
    ) -> Optional[str]:
        """Find a template ID based on platform, content type and client ID."""
        try:
            return template_service.get_template_id(platform, content_type, client_id)
        except Exception as e:
            self.logger.error(f"Error finding template: {e}")
            return None

    async def _generate_with_openai(
        self, system_prompt: str, user_prompt: str, **kwargs
    ) -> str:
        """Helper method for OpenAI API calls"""
        try:
            return await self.openai_service.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt.format(**kwargs)},
                ]
            )
        except Exception as e:
            self.logger.warning(f"OpenAI call failed: {e}")
            return ""

    async def _get_media_urls(
        self, query: str, is_video: bool = False, limit: int = 4
    ) -> List[str]:
        """Helper method to get media URLs"""
        try:
            if is_video:
                return await self.media_service.search_videos(query, limit=limit)
            return await self.media_service.search_images(query, limit=limit)
        except Exception as e:
            self.logger.warning(f"Media search failed: {e}")
            return []
