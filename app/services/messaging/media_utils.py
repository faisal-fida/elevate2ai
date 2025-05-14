import httpx
from typing import Optional
import os
from app.config import settings
from app.services.common.logging import setup_logger

logger = setup_logger(__name__)


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


async def download_media_file(
    media_id: str, media_type: str = "image"
) -> Optional[str]:
    """Download a media file from WhatsApp and save it locally."""
    logger.info(f"Downloading {media_type} with ID: {media_id}")

    # Create media directory if it doesn't exist
    os.makedirs("media", exist_ok=True)

    # Generate a filename based on media ID and type
    file_extension = (
        "jpg" if media_type == "image" else "mp4" if media_type == "video" else "bin"
    )
    filename = f"media/{media_id}.{file_extension}"

    try:
        # Get the media URL first
        media_url = await retrieve_media_url(media_id)
        if not media_url:
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
            with open(filename, "wb") as file:
                file.write(response.content)
                logger.info(
                    f"{media_type.capitalize()} downloaded successfully to {filename}"
                )

            return filename

    except Exception as e:
        logger.error(f"Error downloading media: {str(e)}")
        return None
