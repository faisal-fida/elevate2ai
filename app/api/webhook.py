import traceback
from typing import Dict, Any
from fastapi import APIRouter, Response, Query
from app.config import settings
from app.services.workflow.manager import WorkflowManager
from app.services.common.logging import setup_logger, log_exception

router = APIRouter()
logger = setup_logger(__name__)

workflow_manager: WorkflowManager = WorkflowManager()


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
        logger.error(f"Invalid object in webhook data: {data.get('object')}")
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
            return {"status": "success", "message": "Non-message event processed"}

        message = messages[0]
        sender_id = message.get("from")
        message_type = message.get("type", "unknown")

        logger.info(f"Received {message_type} message from {sender_id}")
        logger.debug(f"Message data: {message}")

        if message_type == "interactive":
            interactive = message.get("interactive", {})
            if "button_reply" in interactive:
                message_text = interactive.get("button_reply", {}).get("id", "")
            elif "list_reply" in interactive:
                message_text = interactive.get("list_reply", {}).get("id", "")
            else:
                logger.error(f"Unknown interactive message format: {interactive}")
                return {
                    "status": "error",
                    "message": "Unknown interactive message format",
                }
        elif message_type in ["image", "video", "document"]:
            # Extract media information
            media_obj = message.get(message_type, {})
            media_id = media_obj.get("id")
            media_mime = media_obj.get("mime_type", "")
            media_sha = media_obj.get("sha256", "")

            if media_id:
                logger.info(
                    f"Received {message_type} with ID: {media_id}, mime: {media_mime}"
                )
                # Create a special message format that our handlers can detect
                message_text = f"Received {message_type} with ID: {media_id}"

                # Store additional metadata in context if needed
                # This could be used later if we need to know more about the media
                context = workflow_manager.state_manager.get_context(sender_id)
                if "media_metadata" not in context:
                    context["media_metadata"] = {}
                context["media_metadata"][media_id] = {
                    "type": message_type,
                    "mime_type": media_mime,
                    "sha256": media_sha,
                }
                workflow_manager.state_manager.update_context(sender_id, context)
            else:
                logger.error(f"Missing media ID for {message_type} message")
                return {
                    "status": "error",
                    "message": f"Missing media ID for {message_type} message",
                }
        elif message_type == "text":
            message_text = message.get("text", {}).get("body", "")
        else:
            # Handle other message types or ignore them
            return {
                "status": "success",
                "message": f"Non-text message of type {message_type} acknowledged but not processed",
            }

        if not sender_id or not message_text:
            logger.error(
                f"Missing sender ID or message text. Sender: {sender_id}, Text: {message_text}"
            )
            return {
                "status": "error",
                "message": "Missing required message data",
            }

        try:
            await workflow_manager.process_message(sender_id, message_text)
            logger.info(f"Successfully processed message from {sender_id}")
            return {"status": "success", "message": "Message processed"}
        except Exception as e:
            error_msg = f"Error in workflow processing for sender {sender_id}"
            log_exception(logger, error_msg, e)
            return {
                "status": "error",
                "message": f"Workflow error: {str(e)}",
                "error_details": {
                    "type": str(type(e).__name__),
                    "sender_id": sender_id,
                    "message_type": message.get("type"),
                },
            }

    except Exception as e:
        error_msg = "Error processing webhook data"
        log_exception(logger, error_msg, e)
        return {
            "status": "error",
            "message": f"Webhook processing error: {str(e)}",
            "error_details": {
                "type": str(type(e).__name__),
                "traceback": traceback.format_exc(),
            },
        }
