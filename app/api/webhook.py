from typing import Dict, Any
from fastapi import Response, Depends
from app.services.whatsapp import WhatsAppService
from app.config import settings
from wa import ContentWorkflow
import logging

logger = logging.getLogger(__name__)

whatsapp_service = WhatsAppService()
workflow = ContentWorkflow(whatsapp_service.messenger)

async def get_whatsapp_service() -> WhatsAppService:
    return whatsapp_service

async def verify_webhook(hub_mode: str, hub_verify_token: str, hub_challenge: str) -> Response:
    """Verify webhook endpoint with WhatsApp API"""
    if hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info(f"Verified webhook with mode: {hub_mode}") 
        return Response(content=hub_challenge, media_type="text/plain")
    logger.error("Webhook verification failed")
    return Response(content="Invalid verification token", status_code=403)

async def handle_message(
    data: Dict[Any, Any],
    whatsapp: WhatsAppService = Depends(get_whatsapp_service)
) -> Dict[str, Any]:
    """Handle incoming WhatsApp messages"""
    try:
        messenger = whatsapp.messenger
        changed_field = messenger.changed_field(data)
        
        if changed_field == "messages":
            if messenger.is_message(data):
                mobile = messenger.get_mobile(data)
                name = messenger.get_name(data)
                message_type = messenger.get_message_type(data)
                
                logger.info(f"New Message; sender:{mobile} name:{name} type:{message_type}")
                
                if message_type == "text":
                    message = messenger.get_message(data)
                    logger.info(f"Message: {message}")
                    await workflow.process_message(mobile, message)
                
                elif message_type == "interactive":
                    message_response = messenger.get_interactive_response(data)
                    interactive_type = message_response.get("type")
                    message_id = message_response[interactive_type]["id"]
                    message_text = message_response[interactive_type]["title"]
                    logger.info(f"Interactive Message; {message_id}: {message_text}")
                
                elif message_type == "location":
                    pass
                    # location = messenger.get_location(data)
                    # latitude = location["latitude"]
                    # longitude = location["longitude"]
                    # logger.info(f"Location: {latitude}, {longitude}")
                
                elif message_type == "image":
                    pass
                    # image = messenger.get_image(data)
                    # image_id, mime_type = image["id"], image["mime_type"]
                    # image_url = await messenger.query_media_url(image_id)
                    # image_filename = await messenger.download_media(image_url, mime_type)
                    # logger.info(f"{mobile} sent image {image_filename}")
                
                elif message_type == "video":
                    pass
                    # video = messenger.get_video(data)
                    # video_id, mime_type = video["id"], video["mime_type"]
                    # video_url = await messenger.query_media_url(video_id)
                    # video_filename = await messenger.download_media(video_url, mime_type)
                    # logger.info(f"{mobile} sent video {video_filename}")
                
                elif message_type == "audio":
                    pass
                    # audio = messenger.get_audio(data)
                    # audio_id, mime_type = audio["id"], audio["mime_type"]
                    # audio_url = await messenger.query_media_url(audio_id)
                    # audio_filename = await messenger.download_media(audio_url, mime_type)
                    # logger.info(f"{mobile} sent audio {audio_filename}")
                
                elif message_type == "document":
                    pass
                    # document = messenger.get_document(data)
                    # doc_id, mime_type = document["id"], document["mime_type"]
                    # doc_url = await messenger.query_media_url(doc_id)
                    # doc_filename = await messenger.download_media(doc_url, mime_type)
                    # logger.info(f"{mobile} sent document {doc_filename}")
                
                else:
                    logger.info(f"{mobile} sent {message_type}")
                    logger.info(data)
            else:
                delivery = messenger.get_delivery(data)
                if delivery:
                    logger.info(f"Message delivery status: {delivery}")
                else:
                    logger.info("No new message")
    
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return {"status": "error", "message": str(e)}
    
    return {"status": "success"}