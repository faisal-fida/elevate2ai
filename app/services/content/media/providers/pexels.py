from typing import List
import httpx
from urllib.parse import quote
from app.config import settings
from app.services.common.logging import setup_logger


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
