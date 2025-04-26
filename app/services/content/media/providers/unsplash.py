from typing import List
import httpx
from urllib.parse import quote
from app.config import settings
from app.services.common.logging import setup_logger


class UnsplashProvider:
    """Provider for Unsplash image search"""

    def __init__(self):
        self.api_key = settings.UNSPLASH_API_KEY
        self.logger = setup_logger(__name__)

    async def search(self, query: str, limit: int, client: httpx.AsyncClient) -> List[str]:
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
