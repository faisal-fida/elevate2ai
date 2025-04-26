from typing import List
from app.services.messaging.state_manager import WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import MESSAGES, SOCIAL_MEDIA_PLATFORMS
from app.services.common.types import WorkflowContext


class PlatformSelectionHandler(BaseHandler):
    """Handler for platform selection state"""

    async def handle(self, client_id: str, message: str) -> None:
        """Handle platform selection"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if message == "done":
            if not context.selected_platforms:
                await self.send_message(client_id, "Please select at least one platform.")
                return

            # Move to content type selection
            self.state_manager.set_state(client_id, WorkflowState.CONTENT_TYPE_SELECTION)

            # Find common content types across selected platforms
            common_types = self._get_common_content_types(context.selected_platforms)
            context.common_content_types = common_types
            self.state_manager.update_context(client_id, vars(context))

            # Send content type options
            await self.send_content_type_options(client_id, common_types)

        elif message in SOCIAL_MEDIA_PLATFORMS:
            # Add platform to selected platforms
            if context.selected_platforms is None:
                context.selected_platforms = []

            if message not in context.selected_platforms:
                context.selected_platforms.append(message)
                self.state_manager.update_context(client_id, vars(context))

            # Send confirmation with selected platforms
            platforms_str = ", ".join(context.selected_platforms)
            await self.send_message(
                client_id, MESSAGES["platform_selection_done"].format(platforms=platforms_str)
            )

            # Send platform options again
            await self.send_platform_options(client_id)

        else:
            await self.send_message(client_id, "Please select a valid platform or type 'done'.")
            await self.send_platform_options(client_id)

    async def send_platform_options(self, client_id: str) -> None:
        """Send platform options to the client"""
        # Create buttons for each platform
        buttons = []
        for platform in SOCIAL_MEDIA_PLATFORMS:
            buttons.append({"id": platform, "title": platform.capitalize()})

        buttons.append({"id": "done", "title": "Done"})

        # Send interactive buttons
        await self.client.send_interactive_buttons(
            header_text="Platform Selection",
            body_text=MESSAGES["platform_selection"],
            buttons=buttons,
            phone_number=client_id,
        )

    async def send_content_type_options(self, client_id: str, content_types: List[str]) -> None:
        """Send content type options to the client"""
        # Create buttons for each content type
        buttons = []
        for content_type in content_types:
            buttons.append({"id": content_type, "title": content_type.capitalize()})

        await self.send_message(client_id, MESSAGES["content_type_selection"])
        # Send interactive buttons
        await self.client.send_interactive_buttons(
            header_text="Content Type Selection",
            body_text=MESSAGES["content_type_selection"],
            buttons=buttons,
            phone_number=client_id,
        )

    def _get_common_content_types(self, platforms: List[str]) -> List[str]:
        """Get content types that are common across all selected platforms"""
        if not platforms:
            return []

        # Get content types for the first platform
        common_types = set(SOCIAL_MEDIA_PLATFORMS[platforms[0]]["content_types"])

        # Intersect with content types from other platforms
        for platform in platforms[1:]:
            platform_types = set(SOCIAL_MEDIA_PLATFORMS[platform]["content_types"])
            common_types = common_types.intersection(platform_types)

        return list(common_types)
