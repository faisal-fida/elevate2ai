from typing import Dict, Any
from fastapi import APIRouter, Response, Query
from app.config import settings
from app.services.messaging.core.whatsapp import WhatsAppClient
from app.services.content.workflow_manager import ContentWorkflow
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

whatsapp_client = WhatsAppClient(
    token=settings.WHATSAPP_TOKEN, phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID
)
workflow = ContentWorkflow(whatsapp_client)


async def get_whatsapp_service() -> WhatsAppClient:
    return whatsapp_client


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> Response:
    if hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info(f"Verified webhook with mode: {hub_mode}")
        return Response(content=hub_challenge, media_type="text/plain")
    logger.error("Webhook verification failed")
    return Response(content="Invalid verification token", status_code=403)


@router.post("/webhook")
async def handle_message(data: Dict[Any, Any]) -> Dict[str, Any]:
    """Handle incoming WhatsApp messages"""
    message = whatsapp_client.extract_message(data)
    if message:
        await workflow.process_message(message)
        return {"status": "ok"}
    return {"status": "no message found"}
