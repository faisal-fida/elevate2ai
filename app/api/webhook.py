import traceback
from typing import Dict, Any
from fastapi import APIRouter, Response, Query
from app.config import settings
from app.services.workflow.manager import WorkflowManager
from app.services.common.logging import setup_logger

router = APIRouter()

# Initialize the workflow manager
workflow_manager = WorkflowManager()
logger = setup_logger(__name__)


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
        # Safely extract entry and changes
        entries = data.get("entry", [])
        if not entries:
            logger.error("No entries in webhook data")
            return {"status": "error", "message": "No entries in webhook data"}

        entry = entries[0]
        changes = entry.get("changes", [])
        if not changes:
            logger.error("No changes in webhook entry")
            return {"status": "error", "message": "No changes in webhook entry"}

        value = changes[0].get("value", {})

        if not value or value.get("messaging_product") != "whatsapp":
            logger.error(f"Invalid message format: {value}")
            return {"status": "error", "message": "Invalid message format"}

        messages = value.get("messages", [])
        if not messages:
            return {"status": "success", "message": "No messages to process"}

        message = messages[0]
        sender_id = message.get("from")

        if message.get("type") == "interactive":
            interactive = message.get("interactive", {})
            logger.info(f"Received interactive message: {interactive}")

            # Handle both button replies and list replies
            if "button_reply" in interactive:
                message_text = interactive.get("button_reply", {}).get("id", "")
                logger.info(f"Extracted button reply ID: {message_text}")
            elif "list_reply" in interactive:
                message_text = interactive.get("list_reply", {}).get("id", "")
                logger.info(f"Extracted list reply ID: {message_text}")
            else:
                logger.error(f"Unknown interactive message format: {interactive}")
                return {
                    "status": "error",
                    "message": "Unknown interactive message format",
                }
        else:
            if message.get("type") != "text":
                logger.info(f"Ignoring non-text message of type: {message.get('type')}")
                return {"status": "success", "message": "Non-text message ignored"}
            message_text = message.get("text", {}).get("body", "")

        if not sender_id or not message_text:
            logger.error("Missing sender ID or message text")
            return {"status": "error", "message": "Missing required message data"}

        logger.info(f"Received message from {sender_id}: {message_text}")
        await workflow_manager.process_message(sender_id, message_text)
        logger.info(f"Successfully processed message from {sender_id}")
        return {"status": "success", "message": "Message processed"}

    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(
            f"Error processing webhook data: {e}\nTraceback:\n{tb_str}\nData:\n{data}"
        )
        return {"status": "error", "message": str(e)}
