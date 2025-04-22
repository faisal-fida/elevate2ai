from typing import Tuple
import logging
from typing import Any, Dict, List, Optional, Union
from openai import AsyncOpenAI
from app.config import settings
from .media_service import search_images_async
from app.constants import OPENAI_PROMPTS

logging.basicConfig(level=logging.INFO)


class AsyncOpenAIService:
    def __init__(self):
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OpenAI API key not provided.")

        self._client = AsyncOpenAI(
            api_key=api_key,
            timeout=settings.OPENAI_TIMEOUT,
            max_retries=settings.OPENAI_MAX_RETRIES,
        )

    async def create_chat_completion(
        self,
        messages: List[Dict[str, Union[str, Any]]],
        model: str = settings.OPENAI_MODEL,
        **kwargs: Any,
    ) -> Optional[str]:
        try:
            completion = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
            return completion.choices[0].message.content if completion.choices else None
        except Exception as e:
            logging.error(f"Error creating chat completion: {e}")
            return None


class ContentGenerator:
    def __init__(self):
        self.openai_service = AsyncOpenAIService()
        self.logger = logging.getLogger(__name__)

    async def generate_content(self, promo_text: str) -> Tuple[str, list[str]]:
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
            image_results = await search_images_async(promo_text_search, limit=4)
            if not image_results or len(image_results) < 4:
                self.logger.warning("Not enough images found, using default.")
                image_results = ["https://example.com/mock-image.jpg"] * 4
                return caption, image_results
            return caption, image_results

        except Exception as e:
            self.logger.error(f"Error generating content: {e}")
            return "Error generating content", ["https://example.com/mock-image.jpg"] * 4
