import asyncio
import logging
from typing import List
from urllib.parse import quote
import httpx
from app.config import settings

logging.basicConfig(level=logging.INFO)


async def unsplash_async(query: str, limit: int, client: httpx.AsyncClient) -> List[str]:
    url = f"https://api.unsplash.com/search/photos?query={quote(query)}&per_page={limit}"
    headers = {
        "Accept-Version": "v1",
        "Authorization": f"Client-ID {settings.UNSPLASH_API_KEY}",
    }
    try:
        resp = await client.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        search_results = resp.json().get("results", [])
        if not search_results:
            logging.warning("No results found from Unsplash.")
            return []
        return [
            item.get("urls", {}).get("raw", "")
            for item in search_results
            if item.get("urls", {}).get("raw")
        ]
    except Exception as e:
        logging.error("Error searching photos from Unsplash: %s", e)
        return []


async def pexels_async(query: str, limit: int, client: httpx.AsyncClient) -> List[str]:
    url = f"https://api.pexels.com/v1/search?query={quote(query)}&per_page={limit}"
    headers = {
        "Authorization": settings.PEXELS_API_KEY,
    }
    try:
        resp = await client.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        search_results = resp.json().get("photos", [])
        if not search_results:
            logging.warning("No results found from Pexels.")
            return []
        return [
            photo.get("src", {}).get("original", "")
            for photo in search_results
            if photo.get("src", {}).get("original")
        ]
    except Exception as e:
        logging.error("Error searching photos from Pexels: %s", e)
        return []


async def pixabay_async(query: str, limit: int, client: httpx.AsyncClient) -> List[str]:
    url = (
        f"https://pixabay.com/api/?key={settings.PIXABAY_API_KEY}"
        f"&q={quote(query)}"
        f"&image_type=photo"
        f"&per_page={limit}"
    )
    try:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [
            photo.get("webformatURL", "")
            for photo in data.get("hits", [])
            if photo.get("webformatURL")
        ]
    except Exception as e:
        logging.error("Error searching photos from Pixabay: %s", e)
        return []


async def search_images_async(query: str, limit: int = 10) -> List[str]:
    """
    Search for images from multiple providers concurrently.
    Returns the first non-empty result list.
    """
    async with httpx.AsyncClient() as client:
        tasks = [
            unsplash_async(query, limit, client),
            pexels_async(query, limit, client),
            pixabay_async(query, limit, client),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for provider_name, result in zip(["unsplash", "pexels", "pixabay"], results):
            if isinstance(result, list) and result:
                logging.info(f"Retrieved results from {provider_name} successfully.")
                return result
            elif isinstance(result, Exception):
                logging.error(f"Error retrieving results from {provider_name}: {result}")
            else:
                logging.warning(f"No results from {provider_name}.")
        logging.warning("All providers returned no results or errors. Returning empty list.")
        return []
