from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import httpx
from app.config import settings

router = APIRouter()


@router.get("/media-proxy")
async def proxy_whatsapp_media(url: str):
    """
    Simple proxy for WhatsApp media URLs
    This endpoint downloads protected WhatsApp media and serves it directly
    """
    if not url or "lookaside.fbsbx.com/whatsapp_business" not in url:
        raise HTTPException(400, "Invalid WhatsApp media URL")

    try:
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            media_type = response.headers.get(
                "content-type", "application/octet-stream"
            )
            return Response(content=response.content, media_type=media_type)
    except Exception as e:
        raise HTTPException(500, f"Failed to proxy media: {str(e)}")
