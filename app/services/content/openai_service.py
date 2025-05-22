from typing import Any, Dict, List, Optional, Union, Tuple
from openai import AsyncOpenAI
from app.config import settings
from app.logging import setup_logger


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
            completion = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
            return completion.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error creating chat completion: {e}")
            return ""

    def validate_user_input(
        self, input_text: str, max_words: int = 5
    ) -> Tuple[bool, str]:
        """
        Validate user input to ensure it meets requirements.
        Returns a tuple of (is_valid, cleaned_text or error_message)
        """
        words = input_text.strip().split()
        if len(words) > max_words:
            return (
                False,
                f"Input exceeds the maximum of {max_words} words. Please provide a shorter input.",
            )

        # Clean and return the validated input
        cleaned = " ".join(words)
        return True, cleaned

    async def generate_formatted_caption(
        self,
        template_type: str,
        context: Dict[str, Any],
        use_emojis: bool = True,
        caption_field: str = "caption_text",
    ) -> str:
        """
        Generate a template-specific, formatted caption with appropriate style and tone.

        Args:
            template_type: Type of content (destination, events, etc.)
            context: Dict containing fields like destination_name, event_name, etc.
            use_emojis: Whether to include emojis in the caption
            caption_field: The field to use for caption ("caption_text" or "post_caption")

        Returns:
            Formatted caption text
        """
        try:
            # Create a system prompt based on template type
            system_prompt = (
                "You are an expert social media copywriter. Create engaging, bright, "
                "and colorful social media captions that are 2-3 sentences long. "
                f"This caption is for a {template_type} post."
            )

            if use_emojis:
                system_prompt += (
                    " Include relevant emojis to make the content engaging."
                )

            # Build user prompt based on the template type and caption field
            user_prompt = ""
            if template_type == "destination":
                user_prompt = f"Create an exciting caption for a travel post about {context.get('destination_name', 'a destination')}. Evoke travel excitement and wanderlust."
            elif template_type == "events":
                user_prompt = f"Create an engaging caption for an event called {context.get('event_name', 'an event')}. Highlight the excitement and key details."
            elif template_type == "promo":
                user_prompt = f"Create a promotional caption for {context.get('promo_text', 'a promotion')}. Make it persuasive with a clear call to action."
            else:
                # Use the appropriate caption field from context
                caption_content = context.get(
                    caption_field, context.get("caption_text", "this topic")
                )
                user_prompt = f"Create a caption for a {template_type} post about {caption_content}."

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            self.logger.info(
                f"Generating formatted caption for {template_type} using {caption_field}"
            )
            return await self.create_chat_completion(messages=messages)
        except Exception as e:
            self.logger.error(f"Error generating formatted caption: {e}")
            return ""

    async def generate_image_search_query(
        self, template_type: str, context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate a search query for finding relevant images based on the template type and context.
        Returns a 2-4 word search query optimized for external media services.

        Args:
            template_type: Type of content (destination, events, etc.)
            context: Dict containing caption and other relevant fields

        Returns:
            Search query string (2-4 words) or default fallback
        """
        try:
            system_prompt = (
                "You are a search query generator for finding relevant images. "
                "Create a concise, specific search query that will find high-quality images "
                "matching the post type and content. The query MUST be 2-4 words only. "
                "Return only the search query, no additional text."
            )

            # Default queries for different template types
            default_queries = {
                "destination": "scenic travel destination",
                "events": "professional business event",
                "promo": "promotional advertisement professional",
                "tips": "business advice tips",
                "seasonal": "seasonal celebration festive",
                "reels": "lifestyle social content",
                "generic": "social media content",
            }

            user_prompt = (
                f"Create a 2-4 word search query for finding images related to a {template_type} post. "
                f"Context: {context.get('caption', '')}. "
            )

            if template_type == "destination":
                user_prompt += f" Destination: {context.get('destination_name', '')}"
            elif template_type == "events":
                user_prompt += f" Event: {context.get('event_name', '')}"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            self.logger.info(f"Generating image search query for {template_type}")
            query = await self.create_chat_completion(messages=messages)

            if query:
                # Clean and validate the query
                query = query.strip("\"'").strip()
                words = query.split()
                if len(words) < 2 or len(words) > 4:
                    self.logger.warning(
                        f"Query '{query}' not within 2-4 words, using default"
                    )
                    return default_queries.get(template_type, "professional content")
                return query

            self.logger.warning(
                f"No query generated, using default for {template_type}"
            )
            return default_queries.get(template_type, "professional content")

        except Exception as e:
            self.logger.error(f"Error generating image search query: {e}")
            return default_queries.get(template_type, "professional content")
