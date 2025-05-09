from typing import List
import httpx
from app.services.common.logging import setup_logger
from urllib.parse import quote
from app.config import settings


class PexelsProvider:
    """Provider for Pexels image search"""

    def __init__(self):
        self.api_key = settings.PEXELS_API_KEY
        self.logger = setup_logger(__name__)

    async def search(
        self, query: str, limit: int, client: httpx.AsyncClient
    ) -> List[str]:
        """Search for images on Pexels"""
        url = f"https://api.pexels.com/v1/search?query={quote(query)}&per_page={limit}"
        headers = {"Authorization": self.api_key}
        try:
            self.logger.info(f"Searching Pexels for '{query}'")
            resp = await client.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return [
                photo.get("src", {}).get("original", "")
                for photo in data.get("photos", [])
            ]
        except Exception as e:
            self.logger.error(f"Error searching photos from Pexels: {e}")
            return []


class PixabayProvider:
    """Provider for Pixabay image search"""

    def __init__(self):
        self.api_key = settings.PIXABAY_API_KEY
        self.logger = setup_logger(__name__)

    async def search(
        self, query: str, limit: int, client: httpx.AsyncClient
    ) -> List[str]:
        """Search for images on Pixabay"""
        url = (
            f"https://pixabay.com/api/?key={self.api_key}"
            f"&q={quote(query)}"
            f"&image_type=photo"
            f"&per_page={limit}"
        )
        try:
            self.logger.info(f"Searching Pixabay for '{query}'")
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return [
                photo.get("webformatURL", "")
                for photo in data.get("hits", [])
                if photo.get("webformatURL")
            ]
        except Exception as e:
            self.logger.error(f"Error searching photos from Pixabay: {e}")
            return []


class UnsplashProvider:
    """Provider for Unsplash image search"""

    def __init__(self):
        self.api_key = settings.UNSPLASH_API_KEY
        self.logger = setup_logger(__name__)

    async def search(
        self, query: str, limit: int, client: httpx.AsyncClient
    ) -> List[str]:
        """Search for images on Unsplash"""
        url = f"https://api.unsplash.com/search/photos?query={quote(query)}&per_page={limit}"
        headers = {
            "Accept-Version": "v1",
            "Authorization": f"Client-ID {self.api_key}",
        }
        try:
            self.logger.info(f"Searching Unsplash for '{query}'")
            resp = await client.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            search_results = resp.json().get("results", [])
            if not search_results:
                self.logger.warning("No results found from Unsplash.")
                return []
            return [
                item.get("urls", {}).get("raw", "")
                for item in search_results
                if item.get("urls", {}).get("raw")
            ]
        except Exception as e:
            self.logger.error(f"Error searching photos from Unsplash: {e}")
            return []


class ImageService:
    def __init__(self):
        self.unsplash = UnsplashProvider()
        self.pexels = PexelsProvider()
        self.pixabay = PixabayProvider()
        self.logger = setup_logger(__name__)

    async def search_images(self, query: str, limit: int = 10) -> List[str]:
        """
        Search for images from providers in priority order: Pexels → Unsplash → Pixabay. Returns the first non-empty result list.
        """
        self.logger.info(f"Searching for images with query: {query}")
        async with httpx.AsyncClient() as client:
            providers = [
                ("pexels", self.pexels.search),
                ("unsplash", self.unsplash.search),
                ("pixabay", self.pixabay.search),
            ]

            for provider_name, search_method in providers:
                try:
                    self.logger.info(f"Querying {provider_name}...")
                    result = await search_method(query, limit, client)
                    if result:
                        self.logger.info(
                            f"Retrieved results from {provider_name} successfully."
                        )
                        return result
                    else:
                        self.logger.warning(f"No results from {provider_name}.")
                except Exception as e:
                    self.logger.error(
                        f"Error retrieving results from {provider_name}: {e}"
                    )

            self.logger.warning(
                "All providers returned no results or errors. Returning empty list."
            )
            return []
