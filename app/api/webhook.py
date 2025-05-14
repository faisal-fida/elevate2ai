import traceback
from typing import Dict, Any

from fastapi import Response
from app.config import settings
from app.services.workflow.manager import WorkflowManager
from app.services.common.logging import setup_logger, log_exception

logger = setup_logger(__name__)
workflow_manager = WorkflowManager()


async def verify_webhook(
    hub_mode: str, hub_verify_token: str, hub_challenge: str
) -> Response:
    """
    Verify webhook request from WhatsApp API
    """
    if hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info(f"Verified webhook with mode: {hub_mode}")
        return Response(content=hub_challenge, media_type="text/plain")

    logger.error("Webhook verification failed")
    return Response(content="Invalid verification token", status_code=403)


async def handle_message(data: Dict[Any, Any]) -> Dict[str, Any]:
    """
    Process incoming WhatsApp message webhook
    """
    # Validate webhook data structure
    if data.get("object") != "whatsapp_business_account":
        logger.error(f"Invalid object in webhook data: {data.get('object')}")
        return {"status": "error", "message": "Invalid object"}

    try:
        # Extract message data from webhook payload
        message_data = extract_message_data(data)
        if not message_data:
            return {"status": "success", "message": "Non-message event processed"}

        # Process the message
        sender_id = message_data["sender_id"]
        message_text = message_data["message_text"]
        message_type = message_data["message_type"]
        is_media_message = message_data["is_media_message"]

        if not sender_id or not message_text:
            logger.error(
                f"Missing sender ID or message text: {sender_id}, {message_text}"
            )
            return {"status": "error", "message": "Missing required message data"}

        # Pass all relevant information to the workflow manager
        await workflow_manager.process_message(
            client_id=sender_id,
            message=message_text,
            message_type=message_type,
            is_media_message=is_media_message,
        )

        logger.info(f"Successfully processed message from {sender_id}")
        return {"status": "success", "message": "Message processed"}

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


def extract_message_data(data: Dict[Any, Any]) -> Dict[str, Any]:
    """
    Extract message data from webhook payload
    Returns None for non-message events
    """
    try:
        # Navigate through the webhook data structure
        entries = data.get("entry", [])
        if not entries:
            logger.error("No entries in webhook data")
            return None

        entry = entries[0]
        changes = entry.get("changes", [])
        if not changes:
            logger.error("No changes in webhook entry")
            return None

        value = changes[0].get("value", {})
        if not value or value.get("messaging_product") != "whatsapp":
            logger.error(f"Invalid message format: {value}")
            return None

        messages = value.get("messages", [])
        if not messages:
            return None

        # Extract message details
        message = messages[0]
        sender_id = message.get("from")
        message_type = message.get("type", "unknown")

        # Handle different message types
        if message_type == "interactive":
            message_text = extract_interactive_message(message)
        elif message_type in ["image", "video", "document"]:
            message_text = handle_media_message(message, message_type, sender_id)
        elif message_type == "text":
            message_text = message.get("text", {}).get("body", "")
        else:
            logger.info(f"Unprocessed message type: {message_type}")
            return None

        # Create a structured response with all necessary information
        return {
            "sender_id": sender_id,
            "message_text": message_text,
            "message_type": message_type,
            "is_media_message": message_type in ["image", "video", "document"],
        }

    except Exception as e:
        logger.error(f"Error extracting message data: {e}")
        return None


def extract_interactive_message(message: Dict[str, Any]) -> str:
    """Extract text from interactive messages (buttons/lists)"""
    interactive = message.get("interactive", {})

    if "button_reply" in interactive:
        return interactive.get("button_reply", {}).get("id", "")
    elif "list_reply" in interactive:
        return interactive.get("list_reply", {}).get("id", "")
    else:
        logger.error(f"Unknown interactive format: {interactive}")
        return ""


def handle_media_message(
    message: Dict[str, Any], message_type: str, sender_id: str
) -> str:
    """
    Process media messages (images, videos, documents) and update context
    Returns a structured message with media type and ID for workflow processing
    """
    media_obj = message.get(message_type, {})
    media_id = media_obj.get("id")
    media_mime = media_obj.get("mime_type", "")
    media_sha = media_obj.get("sha256", "")

    if not media_id:
        logger.error(f"Missing media ID for {message_type} message")
        return ""

    logger.info(f"Received {message_type} with ID: {media_id}, mime: {media_mime}")

    # Store media metadata in user context
    context = workflow_manager.state_manager.get_context(sender_id)

    # Initialize or reset media_metadata if needed
    if "media_metadata" not in context:
        context["media_metadata"] = {}
    elif not isinstance(context["media_metadata"], dict):
        context["media_metadata"] = {}

    # Store the latest media ID for easy access
    context["latest_media_id"] = media_id
    context["latest_media_type"] = message_type

    # Store detailed metadata
    context["media_metadata"][media_id] = {
        "type": message_type,
        "mime_type": media_mime,
        "sha256": media_sha,
    }

    workflow_manager.state_manager.update_context(sender_id, context)

    # Return a structured message that will be used by the workflow
    return f"MEDIA_MESSAGE:{message_type}:{media_id}"
