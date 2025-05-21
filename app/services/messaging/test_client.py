#! TODO: Remove this file
import asyncio
from typing import List, Dict
from app.services.messaging.client import WhatsApp
from app.config import settings

TEST_PHONE_NUMBER = "923408957390"
TEST_TOKEN = settings.WHATSAPP_TOKEN
TEST_PHONE_NUMBER_ID = settings.WHATSAPP_PHONE_NUMBER_ID

TEST_VIDEOS: List[Dict[str, str]] = [
    {
        "type": "video",
        "url": "https://videos.pexels.com/video-files/3912678/3912678-hd_1280_720_25fps.mp4",
        "caption": "Nature video 1",
    }
]


async def main():
    whatsapp = WhatsApp(token=TEST_TOKEN, phone_number_id=TEST_PHONE_NUMBER_ID)
    await whatsapp.send_media(
        media_items=TEST_VIDEOS,
        phone_number=TEST_PHONE_NUMBER,
    )


if __name__ == "__main__":
    asyncio.run(main())
