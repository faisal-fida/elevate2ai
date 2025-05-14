import httpx
from typing import Optional, Tuple
from pathlib import Path
import uuid
from app.config import settings
from app.services.common.logging import setup_logger

logger = setup_logger(__name__)

# Ensure media directories exist
MEDIA_DIR = Path("media")
IMAGES_DIR = MEDIA_DIR / "images"
VIDEOS_DIR = MEDIA_DIR / "videos"

MEDIA_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)
VIDEOS_DIR.mkdir(exist_ok=True)


async def retrieve_media_url(media_id: str) -> Optional[str]:
    """Retrieve a media URL from WhatsApp using the Media ID."""
    logger.info(f"Retrieving media with ID: {media_id}")

    try:
        # Get media URL from WhatsApp Graph API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://graph.facebook.com/v17.0/{media_id}/",
                headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            )

            if response.status_code != 200:
                logger.error(
                    f"Failed to retrieve media URL. Status code: {response.status_code}"
                )
                logger.error(f"Response: {response.text}")
                return None

            data = response.json()

            # Store the URL for later use
            if "url" in data:
                logger.info(f"Successfully retrieved media URL for ID {media_id}")
                return data.get("url")
            else:
                logger.error(f"No URL found in media response: {data}")
                return None

    except Exception as e:
        logger.error(f"Error retrieving media: {str(e)}")
        return None


async def download_media(
    media_id: str, media_type: str = "image"
) -> Optional[Tuple[str, str]]:
    """
    Download a media file from WhatsApp and save it locally.

    Args:
        media_id: The WhatsApp media ID
        media_type: The type of media ("image" or "video")

    Returns:
        Tuple of (local file path, public URL) or None if download failed
    """
    logger.info(f"Downloading {media_type} with ID: {media_id}")

    # Get proper directory
    media_dir = IMAGES_DIR if media_type == "image" else VIDEOS_DIR

    # Generate a unique filename with proper extension
    file_extension = "jpg" if media_type == "image" else "mp4"
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = media_dir / unique_filename

    try:
        # Get the media URL first
        media_url = await retrieve_media_url(media_id)
        if not media_url:
            logger.error(f"Could not retrieve media URL for ID: {media_id}")
            return None

        # Download the file
        async with httpx.AsyncClient() as client:
            response = await client.get(
                media_url,
                headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            )

            if response.status_code != 200:
                logger.error(
                    f"Failed to download media. Status code: {response.status_code}"
                )
                return None

            # Save the file
            with open(file_path, "wb") as file:
                file.write(response.content)

            # Calculate the public URL (media/images/filename.jpg or media/videos/filename.mp4)
            public_url = f"/media/{media_type}s/{unique_filename}"
            logger.info(
                f"{media_type.capitalize()} downloaded successfully to {file_path}"
            )
            logger.info(f"Public URL: {public_url}")

            return str(file_path), public_url

    except Exception as e:
        logger.error(f"Error downloading media: {str(e)}")
        return None


async def download_from_url(
    url: str, media_type: str = "image"
) -> Optional[Tuple[str, str]]:
    """
    Download media from an external URL and save it locally.

    Args:
        url: The external URL
        media_type: The type of media ("image" or "video")

    Returns:
        Tuple of (local file path, public URL) or None if download failed
    """
    logger.info(f"Downloading {media_type} from URL: {url[:50]}...")

    # Get proper directory
    media_dir = IMAGES_DIR if media_type == "image" else VIDEOS_DIR

    # Generate a unique filename with proper extension
    file_extension = "jpg" if media_type == "image" else "mp4"
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = media_dir / unique_filename

    # Check if this is a WhatsApp URL
    is_whatsapp_url = "lookaside.fbsbx.com/whatsapp_business" in url

    try:
        # Download the file
        async with httpx.AsyncClient() as client:
            headers = {}
            if is_whatsapp_url:
                # Add authorization for WhatsApp URLs
                headers["Authorization"] = f"Bearer {settings.WHATSAPP_TOKEN}"

            response = await client.get(url, headers=headers)

            print(f"Response: {response.text}")

            import pdb

            pdb.set_trace()

            if response.status_code != 200:
                logger.error(
                    f"Failed to download from URL. Status code: {response.status_code}"
                )
                return None

            # Save the file
            with open(file_path, "wb") as file:
                file.write(response.content)

            # Calculate the public URL
            public_url = f"/media/{media_type}s/{unique_filename}"
            logger.info(
                f"{media_type.capitalize()} downloaded successfully to {file_path}"
            )
            logger.info(f"Public URL: {public_url}")

            return str(file_path), public_url

    except Exception as e:
        logger.error(f"Error downloading from URL {url}: {str(e)}")
        return None
