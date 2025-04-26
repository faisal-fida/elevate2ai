from typing import List
from app.services.messaging.state_manager import WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import MESSAGES
from app.services.common.types import WorkflowContext


class PlatformSelectionForContentHandler(BaseHandler):
    """Handler for platform selection for a specific content type"""

    async def handle(self, client_id: str, message: str) -> None:
        """Handle platform selection for a content type"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Make sure we have supported platforms
        if not context.supported_platforms:
            await self.send_message(
                client_id, "No supported platforms found for this content type. Please start over."
            )
            self.state_manager.set_state(client_id, WorkflowState.INIT)
            return

        if message == "all":
            # Select all supported platforms
            context.selected_platforms = context.supported_platforms.copy()
            self.state_manager.update_context(client_id, vars(context))

            # Send confirmation message
            platforms_str = ", ".join(
                platform.capitalize() for platform in context.selected_platforms
            )
            await self.send_message(
                client_id, f"You've selected all supported platforms: {platforms_str}"
            )

            # Move to caption input
            await self._proceed_to_caption_input(client_id)

        elif message in context.supported_platforms:
            # Set a single platform
            context.selected_platforms = [message]
            self.state_manager.update_context(client_id, vars(context))

            # Send confirmation message
            await self.send_message(client_id, f"You've selected: {message.capitalize()}")

            # Move to caption input
            await self._proceed_to_caption_input(client_id)

        else:
            await self.send_message(client_id, "Please select a valid platform or 'All'.")
            await self.send_platform_options(
                client_id, context.selected_content_type, context.supported_platforms
            )

    async def _proceed_to_caption_input(self, client_id: str) -> None:
        """Move to caption input"""
        # Set up content types for backward compatibility
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if context.content_types is None:
            context.content_types = {}

        # Set the selected content type for all selected platforms
        for platform in context.selected_platforms:
            context.content_types[platform] = context.selected_content_type

        self.state_manager.update_context(client_id, vars(context))

        # Move to caption input
        self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
        await self.send_message(client_id, MESSAGES["caption_prompt"])

    async def send_platform_options(
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
