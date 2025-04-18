from __future__ import annotations
import os
import mimetypes
import logging
import httpx
from typing import Dict, Any, Optional
from requests_toolbelt.multipart.encoder import MultipartEncoder
from .base import WhatsAppBase


class MediaHandler(WhatsAppBase):
    async def send_image(
        self,
        image: str,
        recipient_id: str,
        caption: Optional[str] = None,
        recipient_type: str = "individual",
    ) -> Dict[str, Any]:
        if os.path.exists(image):
            # Handle local file
            mime_type = mimetypes.guess_type(image)[0]
            media = MultipartEncoder(
                fields={
                    "messaging_product": "whatsapp",
                    "recipient_type": recipient_type,
                    "to": recipient_id,
                    "type": "image",
                    "file": (os.path.basename(image), open(image, "rb"), mime_type),
                }
            )
            headers = self.headers.copy()
            headers["Content-Type"] = media.content_type
        else:
            # Handle URL
            media = {
                "messaging_product": "whatsapp",
                "recipient_type": recipient_type,
                "to": recipient_id,
                "type": "image",
                "image": {"link": image},
            }
            if caption:
                media["image"]["caption"] = caption

        logging.info(f"Sending image to {recipient_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                headers=headers if os.path.exists(image) else self.headers,
                data=media if os.path.exists(image) else None,
                json=media if not os.path.exists(image) else None,
            )

        if response.status_code == 200:
            logging.info(f"Image sent to {recipient_id}")
        else:
            logging.error(f"Failed to send image: {response.text}")
        return response.json()

    async def send_video(
        self,
        video: str,
        recipient_id: str,
        caption: Optional[str] = None,
        recipient_type: str = "individual",
    ) -> Dict[str, Any]:
        if os.path.exists(video):
            mime_type = mimetypes.guess_type(video)[0]
            media = MultipartEncoder(
                fields={
                    "messaging_product": "whatsapp",
                    "recipient_type": recipient_type,
                    "to": recipient_id,
                    "type": "video",
                    "file": (os.path.basename(video), open(video, "rb"), mime_type),
                }
            )
            headers = self.headers.copy()
            headers["Content-Type"] = media.content_type
        else:
            media = {
                "messaging_product": "whatsapp",
                "recipient_type": recipient_type,
                "to": recipient_id,
                "type": "video",
                "video": {"link": video},
            }
            if caption:
                media["video"]["caption"] = caption

        logging.info(f"Sending video to {recipient_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                headers=headers if os.path.exists(video) else self.headers,
                data=media if os.path.exists(video) else None,
                json=media if not os.path.exists(video) else None,
            )

        if response.status_code == 200:
            logging.info(f"Video sent to {recipient_id}")
        else:
            logging.error(f"Failed to send video: {response.text}")
        return response.json()

    async def send_document(
        self,
        document: str,
        recipient_id: str,
        caption: Optional[str] = None,
        recipient_type: str = "individual",
    ) -> Dict[str, Any]:
        """Send a document"""
        if os.path.exists(document):
            mime_type = mimetypes.guess_type(document)[0]
            media = MultipartEncoder(
                fields={
                    "messaging_product": "whatsapp",
                    "recipient_type": recipient_type,
                    "to": recipient_id,
                    "type": "document",
                    "file": (os.path.basename(document), open(document, "rb"), mime_type),
                }
            )
            headers = self.headers.copy()
            headers["Content-Type"] = media.content_type
        else:
            media = {
                "messaging_product": "whatsapp",
                "recipient_type": recipient_type,
                "to": recipient_id,
                "type": "document",
                "document": {"link": document},
            }
            if caption:
                media["document"]["caption"] = caption

        logging.info(f"Sending document to {recipient_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                headers=headers if os.path.exists(document) else self.headers,
                data=media if os.path.exists(document) else None,
                json=media if not os.path.exists(document) else None,
            )

        if response.status_code == 200:
            logging.info(f"Document sent to {recipient_id}")
        else:
            logging.error(f"Failed to send document: {response.text}")
        return response.json()

    async def send_audio(
        self, audio: str, recipient_id: str, recipient_type: str = "individual"
    ) -> Dict[str, Any]:
        """Send an audio message"""
        if os.path.exists(audio):
            mime_type = mimetypes.guess_type(audio)[0]
            media = MultipartEncoder(
                fields={
                    "messaging_product": "whatsapp",
                    "recipient_type": recipient_type,
                    "to": recipient_id,
                    "type": "audio",
                    "file": (os.path.basename(audio), open(audio, "rb"), mime_type),
                }
            )
            headers = self.headers.copy()
            headers["Content-Type"] = media.content_type
        else:
            media = {
                "messaging_product": "whatsapp",
                "recipient_type": recipient_type,
                "to": recipient_id,
                "type": "audio",
                "audio": {"link": audio},
            }

        logging.info(f"Sending audio to {recipient_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                headers=headers if os.path.exists(audio) else self.headers,
                data=media if os.path.exists(audio) else None,
                json=media if not os.path.exists(audio) else None,
            )

        if response.status_code == 200:
            logging.info(f"Audio sent to {recipient_id}")
        else:
            logging.error(f"Failed to send audio: {response.text}")
        return response.json()
