from typing import Dict, Any, List, Optional
from app.services.messaging.client import WhatsApp
from app.services.messaging.state_manager import StateManager, WorkflowState
from app.services.messaging.handlers.base import BaseMessageHandler
from app.constants import MESSAGES
from app.services.common.types import ButtonItem, SectionItem, MediaItem


class WhatsAppHandler(BaseMessageHandler):
    """Handler for WhatsApp messages"""
    
    def __init__(self, client: WhatsApp, state_manager: StateManager):
        super().__init__(client, state_manager)
        self.whatsapp = client  # For type hinting
    
    async def handle_message(self, sender_id: str, message: str) -> Dict[str, Any]:
        """Handle an incoming WhatsApp message"""
        # Process the message based on the current state
        current_state = self.state_manager.get_state(sender_id)
        self.logger.info(f"Handling message from {sender_id} in state {current_state.name}")
        
        # This would typically dispatch to specific handlers based on state
        # For now, just return a simple response
        await self.send_message(sender_id, f"Received message: {message}")
        return {"status": "success"}
    
    async def send_interactive_buttons(
        self, 
        recipient_id: str, 
        header_text: str, 
        body_text: str, 
        buttons: List[ButtonItem]
    ) -> Dict[str, Any]:
        """Send interactive buttons to a recipient"""
        self.logger.info(f"Sending interactive buttons to {recipient_id}")
        return await self.whatsapp.send_interactive_buttons(
            header_text=header_text,
            body_text=body_text,
            buttons=buttons,
            phone_number=recipient_id
        )
    
    async def send_interactive_list(
        self,
        recipient_id: str,
        header_text: str,
        body_text: str,
        button_text: str,
        sections: List[SectionItem]
    ) -> Dict[str, Any]:
        """Send an interactive list to a recipient"""
        self.logger.info(f"Sending interactive list to {recipient_id}")
        return await self.whatsapp.send_interactive_list(
            header_text=header_text,
            body_text=body_text,
            button_text=button_text,
            sections=sections,
            phone_number=recipient_id
        )
    
    async def send_media(
        self,
        recipient_id: str,
        media_items: List[MediaItem]
    ) -> List[Dict[str, Any]]:
        """Send media to a recipient"""
        self.logger.info(f"Sending media to {recipient_id}")
        return await self.whatsapp.send_media(
            media_items=media_items,
            phone_number=recipient_id
        )
