import requests
from urllib.parse import quote
import logging
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config import settings

logging.basicConfig(level=logging.INFO)


def search_images(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    providers = [unsplash, pexels, pixabay]
    results = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(provider, query, limit): provider.__name__
            for provider in providers
        }
        for future in as_completed(futures):
            provider_name = futures[future]
            try:
                provider_results = future.result()
                if provider_results:
                    logging.info(
                        f"Retrieved results from {provider_name} successfully."
                    )
                    return provider_results
                else:
                    logging.warning(
                        f"No results from {provider_name}, checking next provider."
                    )
            except Exception as e:
                logging.error(f"Error retrieving results from {provider_name}: {e}")

    logging.warning(
        "All providers returned no results or errors. Returning empty list."
    )
    return results


def unsplash(query: str, limit: int) -> List[Dict[str, Any]]:
    url = f"https://api.unsplash.com/search/photos?query={query}&per_page={limit}"
    headers = {
        "Accept-Version": "v1",
        "Authorization": f"Client-ID {settings.UNSPLASH_API_KEY}",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        search_results = response.json().get("results", [])

        if not search_results:
            logging.warning("No results found from Unsplash.")
            return []
        return [urls.get("urls", {}).get("raw", "") for urls in search_results]
    except requests.exceptions.RequestException as e:
        logging.error("Error searching photos from Unsplash: %s", e)
        return []


def pexels(query: str, limit: int) -> List[Dict[str, Any]]:
    url = f"https://api.pexels.com/v1/search?query={query}&per_page={limit}"
    headers = {
        "Authorization": settings.PEXELS_API_KEY,
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        search_results = response.json().get("photos", [])

        if not search_results:
            logging.warning("No results found from Pexels.")
            return []
        return [photo.get("src", {}).get("original", "") for photo in search_results]
    except requests.exceptions.RequestException as e:
        logging.error("Error searching photos from Pexels: %s", e)
        return []


def pixabay(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    url = (
        f"https://pixabay.com/api/?key={settings.PIXABAY_API_KEY}"
        f"&q={quote(query)}"
        f"&image_type=photo"
        f"&per_page={limit}"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return [photo.get("webformatURL", "") for photo in data.get("hits", [])]

    except requests.exceptions.RequestException as e:
        logging.error("Error searching photos from Pixabay: %s", e)
        return []


if __name__ == "__main__":
    query = "nature"
    results = search_images(query)
    print(results)
