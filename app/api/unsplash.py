import requests
import logging
from typing import List, Dict, Any
from app.config import settings

logging.basicConfig(level=logging.INFO)


def build_unsplash_url(query: str, limit: int) -> str:
    return f"https://api.unsplash.com/search/photos?query={query}&per_page={limit}"


def get_unsplash_headers() -> Dict[str, str]:
    return {
        "Accept-Version": "v1",
        "Authorization": f"Client-ID {settings.UNSPLASH_API_KEY}",
    }


def search_unsplash_photos(query: str, limit: int) -> List[Dict[str, Any]]:
    url = build_unsplash_url(query, limit)
    headers = get_unsplash_headers()

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("results", [])
    except requests.exceptions.RequestException as e:
        logging.error("Error searching photos from Unsplash: %s", e)
        return []


def main():
    search_results = search_unsplash_photos("mountains", 3)
    if search_results:
        logging.info("Found %d photos from Unsplash search:", len(search_results))
        for photo in search_results:
            logging.info("Photo URL: %s", photo.get("urls", {}).get("raw", ""))
    else:
        logging.warning("No photos found or failed to search photos.")


if __name__ == "__main__":
    main()
