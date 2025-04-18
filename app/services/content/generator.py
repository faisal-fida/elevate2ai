from typing import Tuple
import logging
from typing import Any, Dict, List, Optional, Union
from openai import AsyncOpenAI
from app.config import settings
from .media_service import search_images

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
    def __init__(self, openai_service: AsyncOpenAIService):
        self.openai_service = openai_service
        self.logger = logging.getLogger(__name__)

    async def generate_content(self, promo_text: str) -> Tuple[str, str]:
        """Generate caption and find relevant image for promotional content."""
        try:
            # Generate caption using OpenAI
            messages = [
                {
                    "role": "system",
                    "content": "You are a marketing expert. Create engaging social media captions.",
                },
                {"role": "user", "content": f"Create an engaging caption for: {promo_text}"},
            ]
            caption = await self.openai_service.create_chat_completion(messages=messages)

            if not caption:
                self.logger.warning("No caption generated, using default.")
                caption = f"✨ {promo_text}\n\n#trending #viral #marketing"

            # Find relevant image
            image_results = search_images(promo_text, limit=1)
            image_url = image_results[0] if image_results else "https://example.com/mock-image.jpg"

            if not image_url:
                self.logger.warning("No image found, using mock image.")
                image_url = "https://example.com/mock-image.jpg"

            self.logger.info("Image and caption generated successfully.")
            return caption, image_url

        except Exception as e:
            self.logger.error(f"Error generating content: {e}")
            return (
                f"✨ {promo_text}\n\n#trending #viral #marketing",
                "https://example.com/mock-image.jpg",
            )
