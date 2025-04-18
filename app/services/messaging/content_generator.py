from typing import Tuple
from app.services.chat import AsyncOpenAIService
from app.services.media_manager import search_images
import logging

class ContentGenerator:
    def __init__(self, openai_service: AsyncOpenAIService):
        self.openai_service = openai_service

    async def generate_content(self, promo_text: str) -> Tuple[str, str]:
        """Generate caption and find relevant image for promotional content."""
        try:
            # Generate engaging caption using OpenAI
            messages = [
                {
                    "role": "system",
                    "content": "You are a marketing expert. Create engaging social media captions."
                },
                {
                    "role": "user",
                    "content": f"Create an engaging caption for: {promo_text}"
                }
            ]
            caption = await self.openai_service.create_chat_completion(messages=messages)
            if not caption:
                caption = f"✨ {promo_text}\n\n#trending #viral #marketing"

            # Find relevant image
            image_results = search_images(promo_text, limit=1)
            image_url = image_results[0] if image_results else "https://example.com/mock-image.jpg"

            return caption, image_url

        except Exception as e:
            logging.error(f"Error generating content: {e}")
            return f"✨ {promo_text}\n\n#trending #viral #marketing", "https://example.com/mock-image.jpg"