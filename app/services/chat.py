from typing import Any, Dict, List, Optional, Union
from openai import AsyncOpenAI
import logging
from app.config import settings

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


openai_service = AsyncOpenAIService()


if __name__ == "__main__":
    import asyncio

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. When asked for a list, always respond in JSON format. JSON schema: {names: [string]}",
        },
        {
            "role": "user",
            "content": "Five student names.",
        },
    ]

    response = asyncio.run(
        openai_service.create_chat_completion(
            messages=messages, response_format={"type": "json_object"}
        )
    )

    logging.info(response)
