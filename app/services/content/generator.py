from typing import Tuple, List
from app.services.common.logging import setup_logger
from app.services.content.ai.openai_service import AsyncOpenAIService
from app.services.content.media.image_service import ImageService
from app.constants import OPENAI_PROMPTS


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
                        "content": OPENAI_PROMPTS["caption_user"].format(promo_text=promo_text),
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
                        "content": OPENAI_PROMPTS["search_user"].format(caption=caption),
                    },
                ]
            )
            if not promo_text_search:
                self.logger.warning("No search query generated, using default.")
                promo_text_search = promo_text

            # Search for images
            self.logger.info(f"Generating images for: {promo_text_search}")
            image_results = await self.image_service.search_images(promo_text_search, limit=4)
            if not image_results or len(image_results) < 4:
                self.logger.warning("Not enough images found, using default.")
                image_results = ["https://example.com/mock-image.jpg"] * 4
                return caption, image_results
            return caption, image_results

        except Exception as e:
            self.logger.error(f"Error generating content: {e}")
            return "Error generating content", ["https://example.com/mock-image.jpg"] * 4
