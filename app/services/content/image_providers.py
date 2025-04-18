import logging
from typing import List
import httpx
from urllib.parse import quote
from .base import ImageProvider

logger = logging.getLogger(__name__)


class UnsplashProvider(ImageProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.unsplash.com/search/photos"

    async def search_images(self, query: str, limit: int = 1) -> List[str]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}?query={quote(query)}&per_page={limit}",
                    headers={"Accept-Version": "v1", "Authorization": f"Client-ID {self.api_key}"},
                )
                response.raise_for_status()
                results = response.json().get("results", [])
                return [r["urls"]["raw"] for r in results] if results else []
            except Exception as e:
                logger.error(f"Unsplash search failed: {e}")
                return []


class PexelsProvider(ImageProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.pexels.com/v1/search"

    async def search_images(self, query: str, limit: int = 1) -> List[str]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}?query={quote(query)}&per_page={limit}",
                    headers={"Authorization": self.api_key},
                )
                response.raise_for_status()
                photos = response.json().get("photos", [])
                return [p["src"]["original"] for p in photos] if photos else []
            except Exception as e:
                logger.error(f"Pexels search failed: {e}")
                return []


class CompositeImageProvider(ImageProvider):
    """Tries multiple image providers in sequence until one succeeds"""

    def __init__(self, providers: List[ImageProvider]):
        self.providers = providers

    async def search_images(self, query: str, limit: int = 1) -> List[str]:
        for provider in self.providers:
            try:
                if results := await provider.search_images(query, limit):
                    return results
            except Exception as e:
                logger.error(f"Provider {provider.__class__.__name__} failed: {e}")
                continue
        return []
