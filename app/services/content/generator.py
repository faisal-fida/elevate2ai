from typing import Optional
import logging
from openai import AsyncOpenAI
from .base import ContentProvider, ImageProvider, ContentResult

logger = logging.getLogger(__name__)

class OpenAIContentGenerator(ContentProvider):
    def __init__(
        self,
        api_key: str,
        image_provider: ImageProvider,
        model: str = "gpt-4-turbo-preview",
        timeout: float = 30.0,
        max_retries: int = 2
    ):
        self.image_provider = image_provider
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries
        )
        self.model = model

    async def generate_caption(self, text: str) -> str:
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a marketing expert. Create engaging social media captions."
                    },
                    {"role": "user", "content": f"Create an engaging caption for: {text}"}
                ]
            )
            return completion.choices[0].message.content or text
        except Exception as e:
            logger.error(f"Failed to generate caption: {e}")
            return f"✨ {text}\n\n#trending #marketing"

    async def get_image(self, query: str) -> Optional[str]:
        try:
            results = await self.image_provider.search_images(query, limit=1)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Failed to get image: {e}")
            return None

    async def generate_content(self, text: str) -> ContentResult:
        """Generate both caption and image for the given text"""
        caption = await self.generate_caption(text)
        image_url = await self.get_image(text)
        return ContentResult(caption=caption, image_url=image_url)
