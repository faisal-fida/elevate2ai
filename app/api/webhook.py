from typing import Dict, Any
from fastapi import APIRouter, Response, Query
from app.config import settings
from app.services.content.workflow_manager import ContentWorkflow
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

workflow = ContentWorkflow()


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
    if data.get("object") != "whatsapp_business_account":
        logger.error("Invalid object in webhook data")
        return {"status": "error", "message": "Invalid object"}

    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})

        if not value or value.get("messaging_product") != "whatsapp":
            logger.error("Invalid message format")
            return {"status": "error", "message": "Invalid message format"}

        messages = value.get("messages", [])
        if not messages:
            return {"status": "success", "message": "No messages to process"}

        message = messages[0]
        if message.get("type") != "text":
            logger.info(f"Ignoring non-text message of type: {message.get('type')}")
            return {"status": "success", "message": "Non-text message ignored"}

        sender_id = message.get("from")
        message_text = message.get("text", {}).get("body", "")

        if not sender_id or not message_text:
            logger.error("Missing sender ID or message text")
            return {"status": "error", "message": "Missing required message data"}

        await workflow.process_message(sender_id, message_text)
        logger.info(f"Successfully processed message from {sender_id}")

        return {"status": "success", "message": "Message processed"}

    except Exception as e:
        logger.error(f"Error processing webhook data: {e}")
        return {"status": "error", "message": str(e)}
