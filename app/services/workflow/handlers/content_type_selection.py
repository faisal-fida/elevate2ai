from typing import List, Set
from app.services.messaging.state_manager import WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import (
    MESSAGES,
    SOCIAL_MEDIA_PLATFORMS,
    get_platforms_for_content_type,
)
from app.services.common.types import WorkflowContext


class ContentTypeSelectionHandler(BaseHandler):
    """Handler for content type selection state"""

    async def handle(self, client_id: str, message: str) -> None:
        """Handle content type selection"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Get all available content types across all platforms
        all_content_types = self._get_all_content_types()

        if message in all_content_types:
            # Store the selected content type
            context.selected_content_type = message

            # Find platforms that support this content type
            supported_platforms = get_platforms_for_content_type(message)
            context.supported_platforms = supported_platforms

            # Update context
            self.state_manager.update_context(client_id, context.model_dump())

            # Move to platform selection for this content type
            self.state_manager.set_state(
                client_id, WorkflowState.PLATFORM_SELECTION_FOR_CONTENT
            )

            # Send platform options
            await self.send_platform_options_for_content(
                client_id, message, supported_platforms
            )
        else:
            await self.send_message(client_id, "Please select a valid content type.")
            await self.send_content_type_options(client_id)

    async def send_content_type_options(self, client_id: str) -> None:
        """Send content type options to the client"""
        # Get all available content types
        all_content_types = self._get_all_content_types()

        # Create buttons for each content type
        buttons = []
        for content_type in all_content_types:
            buttons.append({"id": content_type, "title": content_type.capitalize()})

        # Send interactive buttons (will automatically use list if > 3 buttons)
        await self.client.send_interactive_buttons(
            header_text="Content Type Selection",
            body_text=MESSAGES["content_type_selection"],
            buttons=buttons,
            phone_number=client_id,
        )

    async def send_platform_options_for_content(
        self, client_id: str, content_type: str, supported_platforms: List[str]
    ) -> None:
        """Send platform options for the selected content type"""
        # Create buttons for each supported platform
        buttons = []
        for platform in supported_platforms:
            buttons.append({"id": platform, "title": platform.capitalize()})

        # Add "All" option if there are multiple platforms
        if len(supported_platforms) > 1:
            buttons.append({"id": "all", "title": "All Platforms"})

        # Send message with platform options
        await self.client.send_interactive_buttons(
            header_text=f"Platforms for {content_type.capitalize()}",
            body_text=MESSAGES["platform_selection_for_content"].format(
                content_type=content_type.capitalize()
            ),
            buttons=buttons,
            phone_number=client_id,
        )

    def _get_all_content_types(self) -> List[str]:
        """Get all available content types across all platforms"""
        all_types: Set[str] = set()

        for platform_data in SOCIAL_MEDIA_PLATFORMS.values():
            all_types.update(platform_data["content_types"])

        return sorted(list(all_types))
