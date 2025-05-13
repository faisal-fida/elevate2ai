from typing import List, Literal
import httpx
from app.services.common.logging import setup_logger
from urllib.parse import quote
from app.config import settings

MediaType = Literal["image", "video"]


class PexelsProvider:
    """Provider for Pexels image and video search"""

    def __init__(self):
        self.api_key = settings.PEXELS_API_KEY
        self.logger = setup_logger(__name__)

    async def search_images(
        self, query: str, limit: int, client: httpx.AsyncClient
    ) -> List[str]:
        """Search for images on Pexels"""
        url = f"https://api.pexels.com/v1/search?query={quote(query)}&per_page={limit}"
        headers = {"Authorization": self.api_key}
        try:
            self.logger.info(f"Searching Pexels for images '{query}'")
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

    async def search_videos(
        self, query: str, limit: int, client: httpx.AsyncClient
    ) -> List[str]:
        """Search for videos on Pexels"""
        url = f"https://api.pexels.com/videos/search?query={quote(query)}&per_page={limit}"
        headers = {"Authorization": self.api_key}
        try:
            self.logger.info(f"Searching Pexels for videos '{query}'")
            resp = await client.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            video_urls = []
            for video in data.get("videos", []):
                video_files = video.get("video_files", [])
                if video_files:
                    # Get HD or highest quality available
                    hd_files = [f for f in video_files if f.get("quality") == "hd"]
                    if hd_files:
                        video_urls.append(hd_files[0].get("link", ""))
                    elif video_files:
                        video_urls.append(video_files[0].get("link", ""))
            return video_urls
        except Exception as e:
            self.logger.error(f"Error searching videos from Pexels: {e}")
            return []


class PixabayProvider:
    """Provider for Pixabay image and video search"""

    def __init__(self):
        self.api_key = settings.PIXABAY_API_KEY
        self.logger = setup_logger(__name__)

    async def search_images(
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
            self.logger.info(f"Searching Pixabay for images '{query}'")
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

    async def search_videos(
        self, query: str, limit: int, client: httpx.AsyncClient
    ) -> List[str]:
        """Search for videos on Pixabay"""
        url = (
            f"https://pixabay.com/api/videos/?key={self.api_key}"
            f"&q={quote(query)}"
            f"&per_page={limit}"
        )
        try:
            self.logger.info(f"Searching Pixabay for videos '{query}'")
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            video_urls = []
            for video in data.get("hits", []):
                videos = video.get("videos", {})
                # Try to get HD or medium quality
                for quality in ["large", "medium"]:
                    if quality in videos and videos[quality].get("url"):
                        video_urls.append(videos[quality].get("url"))
                        break
            return video_urls
        except Exception as e:
            self.logger.error(f"Error searching videos from Pixabay: {e}")
            return []


class UnsplashProvider:
    """Provider for Unsplash image search"""

    def __init__(self):
        self.api_key = settings.UNSPLASH_API_KEY
        self.logger = setup_logger(__name__)

    async def search_images(
        self, query: str, limit: int, client: httpx.AsyncClient
    ) -> List[str]:
        """Search for images on Unsplash"""
        url = f"https://api.unsplash.com/search/photos?query={quote(query)}&per_page={limit}"
        headers = {
            "Accept-Version": "v1",
            "Authorization": f"Client-ID {self.api_key}",
        }
        try:
            self.logger.info(f"Searching Unsplash for images '{query}'")
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


class MediaService:
    """Service for searching and handling both images and videos"""

    def __init__(self):
        self.unsplash = UnsplashProvider()
        self.pexels = PexelsProvider()
        self.pixabay = PixabayProvider()
        self.logger = setup_logger(__name__)

    async def search_images(self, query: str, limit: int = 10) -> List[str]:
        """
        Search for images from providers in priority order: Pexels → Unsplash → Pixabay.
        Returns the first non-empty result list.
        """
        async with httpx.AsyncClient() as client:
            providers = [
                ("pexels", self.pexels.search_images),
                ("unsplash", self.unsplash.search_images),
                ("pixabay", self.pixabay.search_images),
            ]

            for provider_name, search_method in providers:
                try:
                    result = await search_method(query, limit, client)
                    if result:
                        self.logger.info(
                            f"Retrieved image results from {provider_name} successfully."
                        )
                        return result
                    else:
                        self.logger.warning(f"No image results from {provider_name}.")
                except Exception as e:
                    self.logger.error(
                        f"Error retrieving image results from {provider_name}: {e}"
                    )

            self.logger.warning(
                "All providers returned no image results or errors. Returning empty list."
            )
            return []

    async def search_videos(self, query: str, limit: int = 10) -> List[str]:
        """
        Search for videos from providers in priority order: Pexels → Pixabay.
        Returns the first non-empty result list.
        """
        async with httpx.AsyncClient() as client:
            providers = [
                ("pexels", self.pexels.search_videos),
                ("pixabay", self.pixabay.search_videos),
            ]

            for provider_name, search_method in providers:
                try:
                    result = await search_method(query, limit, client)
                    if result:
                        self.logger.info(
                            f"Retrieved video results from {provider_name} successfully."
                        )
                        return result
                    else:
                        self.logger.warning(f"No video results from {provider_name}.")
                except Exception as e:
                    self.logger.error(
                        f"Error retrieving video results from {provider_name}: {e}"
                    )

            self.logger.warning(
                "All providers returned no video results or errors. Returning empty list."
            )
            return []

    async def search_media(
        self, query: str, media_type: MediaType = "image", limit: int = 10
    ) -> List[str]:
        """
        Search for media of the specified type.

        Args:
            query: The search query
            media_type: Type of media to search for ("image" or "video")
            limit: Maximum number of results to return

        Returns:
            List of media URLs
        """
        if media_type == "video":
            return await self.search_videos(query, limit)
        else:
            return await self.search_images(query, limit)
