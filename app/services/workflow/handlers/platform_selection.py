from typing import List
from app.services.messaging.state_manager import WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import MESSAGES, SOCIAL_MEDIA_PLATFORMS
from app.services.types import WorkflowContext


class PlatformSelectionHandler(BaseHandler):
    """Handler for platform selection state"""

    async def handle(self, client_id: str, message: str) -> None:
        """Handle platform selection"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if message == "all":
            context.selected_platforms = list(SOCIAL_MEDIA_PLATFORMS.keys())
            self.state_manager.update_context(client_id, vars(context))

            platforms_str = ", ".join(
                platform.capitalize() for platform in context.selected_platforms
            )
            await self.send_message(
                client_id, f"You've selected all platforms: {platforms_str}"
            )

            await self._proceed_to_content_type_selection(client_id, context)

        elif message in SOCIAL_MEDIA_PLATFORMS:
            context.selected_platforms = [message]
            self.state_manager.update_context(client_id, vars(context))

            await self.send_message(
                client_id, f"You've selected: {message.capitalize()}"
            )

            await self._proceed_to_content_type_selection(client_id, context)

        else:
            await self.send_message(client_id, "Please select a valid platform.")
            await self.send_platform_options(client_id)

    async def _proceed_to_content_type_selection(
        self, client_id: str, context: WorkflowContext
    ) -> None:
        """Move to content type selection"""
        self.state_manager.set_state(client_id, WorkflowState.CONTENT_TYPE_SELECTION)

        common_types = self._get_common_content_types(context.selected_platforms)
        context.common_content_types = common_types
        self.state_manager.update_context(client_id, vars(context))

        await self.send_content_type_options(client_id, common_types)

    async def send_platform_options(self, client_id: str) -> None:
        """Send platform options to the client"""
        buttons = []
        for platform in SOCIAL_MEDIA_PLATFORMS:
            buttons.append({"id": platform, "title": platform.capitalize()})

        buttons.append({"id": "all", "title": "All Platforms"})

        await self.client.send_interactive_buttons(
            header_text="Platform Selection",
            body_text=MESSAGES["platform_selection"],
            buttons=buttons,
            phone_number=client_id,
        )

    async def send_content_type_options(
        self, client_id: str, content_types: List[str]
    ) -> None:
        """Send content type options to the client"""
        await self.send_message(client_id, MESSAGES["content_type_selection"])

        if not content_types:
            await self.send_message(
                client_id,
                "No common content types found across the selected platforms. Please start over and select different platforms.",
            )
            self.state_manager.set_state(client_id, WorkflowState.PLATFORM_SELECTION)
            await self.send_platform_options(client_id)
            return

        buttons = []
        for content_type in content_types:
            buttons.append({"id": content_type, "title": content_type.capitalize()})

        await self.client.send_interactive_buttons(
            header_text="Content Type Selection",
            body_text="Select a content type for your post:",
            buttons=buttons,
            phone_number=client_id,
        )

    def _get_common_content_types(self, platforms: List[str]) -> List[str]:
        """Get content types that are common across all selected platforms"""
        if not platforms:
            return []

        common_types = set(SOCIAL_MEDIA_PLATFORMS[platforms[0]]["content_types"])

        for platform in platforms[1:]:
            platform_types = set(SOCIAL_MEDIA_PLATFORMS[platform]["content_types"])
            common_types = common_types.intersection(platform_types)

        return list(common_types)
