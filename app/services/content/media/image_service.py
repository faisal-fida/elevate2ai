import asyncio
from typing import List
import httpx
from app.services.common.logging import setup_logger
from app.services.content.media.providers.unsplash import UnsplashProvider
from app.services.content.media.providers.pexels import PexelsProvider
from app.services.content.media.providers.pixabay import PixabayProvider


class ImageService:
    """Service for searching and retrieving images"""
    
    def __init__(self):
        self.unsplash = UnsplashProvider()
        self.pexels = PexelsProvider()
        self.pixabay = PixabayProvider()
        self.logger = setup_logger(__name__)
    
    async def search_images(self, query: str, limit: int = 10) -> List[str]:
        """
        Search for images from multiple providers concurrently.
        Returns the first non-empty result list.
        """
        self.logger.info(f"Searching for images with query: {query}")
        async with httpx.AsyncClient() as client:
            tasks = [
                self.unsplash.search(query, limit, client),
                self.pexels.search(query, limit, client),
                self.pixabay.search(query, limit, client),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for provider_name, result in zip(["unsplash", "pexels", "pixabay"], results):
                if isinstance(result, list) and result:
                    self.logger.info(f"Retrieved results from {provider_name} successfully.")
                    return result
                elif isinstance(result, Exception):
                    self.logger.error(f"Error retrieving results from {provider_name}: {result}")
                else:
                    self.logger.warning(f"No results from {provider_name}.")
            
            self.logger.warning("All providers returned no results or errors. Returning empty list.")
            return []
