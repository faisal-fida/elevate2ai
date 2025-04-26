from typing import List
import httpx
from urllib.parse import quote
from app.config import settings
from app.services.common.logging import setup_logger


class PixabayProvider:
    """Provider for Pixabay image search"""

    def __init__(self):
        self.api_key = settings.PIXABAY_API_KEY
        self.logger = setup_logger(__name__)

    async def search(self, query: str, limit: int, client: httpx.AsyncClient) -> List[str]:
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
