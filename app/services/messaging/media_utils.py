import httpx
from typing import Optional
from pathlib import Path
import uuid
import os
from app.config import settings
from app.logging import setup_logger

logger = setup_logger(__name__)

# Ensure media directory exists
MEDIA_DIR = Path("media")
IMAGES_DIR = MEDIA_DIR / "images"
MEDIA_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

# Store active media files for cleanup later
active_media = {}


async def save_whatsapp_image(media_id: str, client_id: str) -> Optional[str]:
    """
    Download and save an image from WhatsApp media ID.

    Args:
        media_id: The WhatsApp media ID
        client_id: Client identifier for tracking active media

    Returns:
        Public URL to access the image or None if download failed
    """
    logger.info(f"Processing WhatsApp image with ID: {media_id} for client {client_id}")

    try:
        # Step 1: Get media URL from WhatsApp API
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

            if "url" not in data:
                logger.error(f"No URL found in media response: {data}")
                return None

            whatsapp_url = data["url"]
            logger.info(f"Successfully retrieved WhatsApp URL for ID {media_id}")

        # Step 2: Download the image
        async with httpx.AsyncClient() as client:
            response = await client.get(
                whatsapp_url,
                headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            )

            if response.status_code != 200:
                logger.error(
                    f"Failed to download image. Status code: {response.status_code}"
                )
                return None

            # Step 3: Save to local file with unique name
            unique_filename = f"{uuid.uuid4()}.jpg"
            file_path = IMAGES_DIR / unique_filename

            with open(file_path, "wb") as file:
                file.write(response.content)

            # Step 4: Create public URL and track for cleanup
            public_url = f"/media/images/{unique_filename}"

            # Track this file for later cleanup
            active_media[client_id] = active_media.get(client_id, []) + [str(file_path)]

            logger.info(f"Image saved to {file_path}")
            logger.info(f"Public URL: {public_url}")

            return public_url

    except Exception as e:
        logger.error(f"Error processing WhatsApp image: {str(e)}")
        return None


def cleanup_client_media(client_id: str) -> None:
    """
    Clean up all media files for a specific client.

    Args:
        client_id: Client identifier whose media files should be deleted
    """
    if client_id not in active_media:
        return

    for file_path in active_media[client_id]:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted media file: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting media file {file_path}: {str(e)}")

    # Clear tracking data
    active_media.pop(client_id, None)
    logger.info(f"Cleaned up all media for client {client_id}")
