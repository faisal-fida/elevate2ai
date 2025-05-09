from typing import Any, Dict, List, Optional, Union
from openai import AsyncOpenAI
from app.config import settings
from app.services.common.logging import setup_logger


class AsyncOpenAIService:
    """Service for interacting with OpenAI API"""

    def __init__(self):
        self.logger = setup_logger(__name__)
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
        """Create a chat completion using OpenAI API"""
        try:
            self.logger.info(f"Creating chat completion with model {model}")
            completion = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
            return completion.choices[0].message.content if completion.choices else None
        except Exception as e:
            self.logger.error(f"Error creating chat completion: {e}")
            return None
