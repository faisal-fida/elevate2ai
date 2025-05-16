from typing import List, Set
from app.services.messaging.state_manager import WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import (
    MESSAGES,
    SOCIAL_MEDIA_PLATFORMS,
)
from app.services.common.types import WorkflowContext


class ContentTypeSelectionHandler(BaseHandler):
    """Handler for content type selection state"""

    async def handle(self, client_id: str, message: str) -> None:
        """Handle content type selection"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        all_content_types = self._get_all_content_types()

        if message in all_content_types:
            context.selected_content_type = message
            supported_platforms = self._get_platforms_for_content_type(message)
            context.supported_platforms = supported_platforms
            self.state_manager.update_context(client_id, context.model_dump())
            self.state_manager.set_state(
                client_id, WorkflowState.PLATFORM_SELECTION_FOR_CONTENT
            )
            await self.send_platform_options_for_content(
                client_id, message, supported_platforms
            )
        else:
            await self.send_message(client_id, "Please select a valid content type.")
            await self.send_content_type_options(client_id)

    def _get_platforms_for_content_type(self, content_type: str) -> list:
        """Return a list of platforms that support the given content type"""
        supported_platforms = []
        for platform, details in SOCIAL_MEDIA_PLATFORMS.items():
            if content_type in details["content_types"]:
                supported_platforms.append(platform)
        return supported_platforms

    async def send_content_type_options(self, client_id: str) -> None:
        """Send content type options to the client"""
        all_content_types = self._get_all_content_types()
        buttons = []
        for content_type in all_content_types:
            buttons.append({"id": content_type, "title": content_type.capitalize()})
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
        buttons = []
        for platform in supported_platforms:
            buttons.append({"id": platform, "title": platform.capitalize()})

        if len(supported_platforms) > 1:
            buttons.append({"id": "all", "title": "All Platforms"})

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
