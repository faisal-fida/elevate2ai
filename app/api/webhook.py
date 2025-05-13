import traceback
from typing import Dict, Any
from fastapi import APIRouter, Response, Query
from app.config import settings
from app.services.workflow.manager import WorkflowManager
from app.services.common.logging import setup_logger, log_exception

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
    # Generate a unique request ID for tracking this request through logs
    request_id = id(data) % 10000
    logger.info(f"[RequestID:{request_id}] Processing webhook request")

    if data.get("object") != "whatsapp_business_account":
        logger.error(
            f"[RequestID:{request_id}] Invalid object in webhook data: {data.get('object')}"
        )
        return {
            "status": "error",
            "message": "Invalid object",
            "request_id": request_id,
        }

    try:
        # Safely extract entry and changes
        entries = data.get("entry", [])
        if not entries:
            logger.error(f"[RequestID:{request_id}] No entries in webhook data")
            return {
                "status": "error",
                "message": "No entries in webhook data",
                "request_id": request_id,
            }

        entry = entries[0]
        changes = entry.get("changes", [])
        if not changes:
            logger.error(f"[RequestID:{request_id}] No changes in webhook entry")
            return {
                "status": "error",
                "message": "No changes in webhook entry",
                "request_id": request_id,
            }

        value = changes[0].get("value", {})

        if not value or value.get("messaging_product") != "whatsapp":
            logger.error(f"[RequestID:{request_id}] Invalid message format: {value}")
            return {
                "status": "error",
                "message": "Invalid message format",
                "request_id": request_id,
            }

        messages = value.get("messages", [])
        if not messages:
            # This might be a delivery receipt or other non-message event
            logger.info(f"[RequestID:{request_id}] Received non-message event")
            return {
                "status": "success",
                "message": "Non-message event processed",
                "request_id": request_id,
            }

        message = messages[0]
        sender_id = message.get("from")

        if message.get("type") == "interactive":
            interactive = message.get("interactive", {})
            logger.info(
                f"[RequestID:{request_id}] Received interactive message: {interactive}"
            )

            # Handle both button replies and list replies
            if "button_reply" in interactive:
                message_text = interactive.get("button_reply", {}).get("id", "")
                logger.info(
                    f"[RequestID:{request_id}] Extracted button reply ID: {message_text}"
                )
            elif "list_reply" in interactive:
                message_text = interactive.get("list_reply", {}).get("id", "")
                logger.info(
                    f"[RequestID:{request_id}] Extracted list reply ID: {message_text}"
                )
            else:
                logger.error(
                    f"[RequestID:{request_id}] Unknown interactive message format: {interactive}"
                )
                return {
                    "status": "error",
                    "message": "Unknown interactive message format",
                    "request_id": request_id,
                }
        else:
            if message.get("type") != "text":
                message_type = message.get("type", "unknown")
                logger.info(
                    f"[RequestID:{request_id}] Received non-text message of type: {message_type}"
                )

                # Handle media messages like images, videos, etc.
                if message_type in ["image", "video", "document"]:
                    # In a real implementation, we would process the media
                    logger.info(
                        f"[RequestID:{request_id}] Media message received: {message_type}"
                    )
                    message_text = f"[{message_type}]"  # Placeholder
                else:
                    # Skip other message types
                    return {
                        "status": "success",
                        "message": f"Non-text message of type {message_type} ignored",
                        "request_id": request_id,
                    }
            else:
                message_text = message.get("text", {}).get("body", "")

        if not sender_id or not message_text:
            logger.error(
                f"[RequestID:{request_id}] Missing sender ID or message text. Sender: {sender_id}, Text: {message_text}"
            )
            return {
                "status": "error",
                "message": "Missing required message data",
                "request_id": request_id,
            }

        logger.info(
            f"[RequestID:{request_id}] Received message from {sender_id}: {message_text}"
        )
        try:
            await workflow_manager.process_message(sender_id, message_text)
            logger.info(
                f"[RequestID:{request_id}] Successfully processed message from {sender_id}"
            )
            return {
                "status": "success",
                "message": "Message processed",
                "request_id": request_id,
            }
        except Exception as e:
            # Log the workflow processing error with detailed traceback
            error_msg = f"[RequestID:{request_id}] Error in workflow processing for sender {sender_id}"
            log_exception(logger, error_msg, e)
            return {
                "status": "error",
                "message": f"Workflow error: {str(e)}",
                "request_id": request_id,
                "error_details": {
                    "type": str(type(e).__name__),
                    "sender_id": sender_id,
                    "message_type": message.get("type"),
                },
            }

    except Exception as e:
        # Log the webhook handling error with detailed traceback
        error_id = f"webhook_{request_id}_{id(e) % 10000}"
        error_msg = f"[RequestID:{request_id}] Error processing webhook data. Error ID: {error_id}"
        log_exception(logger, error_msg, e)

        return {
            "status": "error",
            "message": f"Error ID: {error_id}. Please provide this ID to support.",
            "request_id": request_id,
        }
