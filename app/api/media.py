from fastapi import APIRouter, Depends, Query
from typing import Optional, Literal
from pydantic import BaseModel
import requests
from app.config import settings
from app.api.auth import get_user_dependency
from app.models.user import UserInDB

router = APIRouter()

MediaSource = Literal["pexels", "unsplash", "pixabay"]


class MediaItem(BaseModel):
    url: str
    width: int
    height: int
    photographer: Optional[str] = None


class MediaSearchResponse(BaseModel):
    images: list[MediaItem]
    videos: list[MediaItem]


def search_pexels(query: str, limit: int):
    headers = {"Authorization": settings.PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={query}&per_page={limit}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return [
            MediaItem(
                url=photo["src"]["large"],
                width=photo["width"],
                height=photo["height"],
                photographer=photo["photographer"],
            )
            for photo in data.get("photos", [])
        ]
    return []


def search_unsplash(query: str, limit: int):
    headers = {"Authorization": f"Client-ID {settings.UNSPLASH_API_KEY}"}
    url = f"https://api.unsplash.com/search/photos?query={query}&per_page={limit}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return [
            MediaItem(
                url=photo["urls"]["regular"],
                width=photo["width"],
                height=photo["height"],
                photographer=photo["user"]["name"],
            )
            for photo in data.get("results", [])
        ]
    return []


def search_pixabay(query: str, limit: int):
    params = {"key": settings.PIXABAY_API_KEY, "q": query, "per_page": limit}
    response = requests.get("https://pixabay.com/api/", params=params)
    if response.status_code == 200:
        data = response.json()
        return [
            MediaItem(
                url=photo["webformatURL"],
                width=photo["webformatWidth"],
                height=photo["webformatHeight"],
                photographer=photo["user"],
            )
            for photo in data.get("hits", [])
        ]
    return []


@router.get("/search", response_model=MediaSearchResponse)
async def search_media(
    query: str = Query(..., min_length=2, description="Search query for media"),
    fallback: bool = Query(True, description="Whether to use fallback services"),
    limit: int = Query(4, ge=1, le=20, description="Number of results to return"),
    current_user: UserInDB = Depends(get_user_dependency()),
):
    """
    Unified media search across Pexels, Unsplash, and Pixabay
    """
    search_order = []
    if fallback:
        search_order = ["pexels", "unsplash", "pixabay"]

    images = []
    videos = []

    for service in search_order:
        try:
            if service == "pexels":
                images = search_pexels(query, limit)
            elif service == "unsplash":
                images = search_unsplash(query, limit)
            elif service == "pixabay":
                images = search_pixabay(query, limit)

            if images:
                break
        except Exception:
            continue

    return MediaSearchResponse(images=images, videos=videos)
