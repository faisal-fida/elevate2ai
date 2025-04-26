from typing import List
from app.services.messaging.state_manager import WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import MESSAGES, SOCIAL_MEDIA_PLATFORMS
from app.services.common.types import WorkflowContext


class ContentTypeHandler(BaseHandler):
    """Handler for content type selection state"""

    async def handle(self, client_id: str, message: str) -> None:
        """Handle content type selection"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if message in context.common_content_types:
            # Set content type for all platforms
            if context.content_types is None:
                context.content_types = {}

            for platform in context.selected_platforms:
                context.content_types[platform] = message

            self.state_manager.update_context(client_id, vars(context))

            # For single platform selection, skip the same content confirmation
            if len(context.selected_platforms) == 1:
                context.same_content_across_platforms = True
                self.state_manager.update_context(client_id, vars(context))

                # Move directly to caption input
                self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
                await self.send_message(client_id, MESSAGES["caption_prompt"])
            else:
                # For multiple platforms, ask if user wants to use the same content
                self.state_manager.set_state(client_id, WorkflowState.SAME_CONTENT_CONFIRMATION)
                await self.send_same_content_confirmation(client_id)

        else:
            await self.send_message(client_id, "Please select a valid content type.")
            await self.send_content_type_options(client_id, context.common_content_types)

    async def handle_confirmation(self, client_id: str, message: str) -> None:
        """Handle same content confirmation"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # This method is only called for multiple platforms (All Platforms option)
        if message in ["yes", "y"]:
            context.same_content_across_platforms = True
            self.state_manager.update_context(client_id, vars(context))

            # Move to caption input
            self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
            await self.send_message(client_id, MESSAGES["caption_prompt"])

        elif message in ["no", "n"]:
            context.same_content_across_platforms = False
            context.current_platform_index = 0
            self.state_manager.update_context(client_id, vars(context))

            # Move to platform-specific content
            self.state_manager.set_state(client_id, WorkflowState.PLATFORM_SPECIFIC_CONTENT)
            await self.handle_platform_specific(client_id, "")

        else:
            await self.send_message(client_id, "Please reply with 'yes' or 'no'.")
            await self.send_same_content_confirmation(client_id)

    async def handle_platform_specific(self, client_id: str, message: str) -> None:
        """Handle platform-specific content selection"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # If this is not the first call, process the message
        if message and context.current_platform_index > 0:
            current_platform = context.selected_platforms[context.current_platform_index - 1]
            platform_content_types = SOCIAL_MEDIA_PLATFORMS[current_platform]["content_types"]

            if message in platform_content_types:
                # Set content type for the current platform
                if context.content_types is None:
                    context.content_types = {}

                context.content_types[current_platform] = message
                self.state_manager.update_context(client_id, vars(context))
            else:
                await self.send_message(client_id, "Please select a valid content type.")
                await self.send_platform_content_types(
                    client_id,
                    current_platform,
                    SOCIAL_MEDIA_PLATFORMS[current_platform]["content_types"],
                )
                return

        # Move to the next platform or to caption input
        if context.current_platform_index < len(context.selected_platforms):
            current_platform = context.selected_platforms[context.current_platform_index]
            context.current_platform_index += 1
            self.state_manager.update_context(client_id, vars(context))

            await self.send_platform_content_types(
                client_id,
                current_platform,
                SOCIAL_MEDIA_PLATFORMS[current_platform]["content_types"],
            )
        else:
            # All platforms have been processed, move to caption input
            self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)
            await self.send_message(client_id, MESSAGES["caption_prompt"])

    async def send_content_type_options(self, client_id: str, content_types: List[str]) -> None:
        """Send content type options to the client"""
        # Send message first to provide context
        await self.send_message(client_id, MESSAGES["content_type_selection"])

        # Check if there are any content types
        if not content_types:
            await self.send_message(
                client_id,
                "No common content types found across the selected platforms. Please start over and select different platforms.",
            )
            # Reset to platform selection
            self.state_manager.set_state(client_id, WorkflowState.PLATFORM_SELECTION)
            # Send platform options again
            from app.services.workflow.handlers.platform_selection import PlatformSelectionHandler

            platform_handler = PlatformSelectionHandler(self.client, self.state_manager)
            await platform_handler.send_platform_options(client_id)
            return

        # Create buttons for each content type
        buttons = []
        for content_type in content_types:
            buttons.append({"id": content_type, "title": content_type.capitalize()})

        # Send interactive buttons (will automatically use list if > 3 buttons)
        await self.client.send_interactive_buttons(
            header_text="Content Type Selection",
            body_text="Select a content type for your post:",
            buttons=buttons,
            phone_number=client_id,
        )

    async def send_same_content_confirmation(self, client_id: str) -> None:
        """Send same content confirmation to the client"""
        # Create yes/no buttons
        buttons = [{"id": "yes", "title": "Yes"}, {"id": "no", "title": "No"}]

        # Send interactive buttons
        await self.client.send_interactive_buttons(
            header_text="Content Confirmation",
            body_text=MESSAGES["same_content_prompt"],
            buttons=buttons,
            phone_number=client_id,
        )

    async def send_platform_content_types(
        self, client_id: str, platform: str, content_types: List[str]
    ) -> None:
        """Send platform-specific content types to the client"""
        # Send message first to provide context
        await self.send_message(
            client_id, MESSAGES["platform_specific_content"].format(platform=platform.capitalize())
        )

        # Check if there are any content types
        if not content_types:
            await self.send_message(
                client_id,
                f"No content types available for {platform.capitalize()}. Please start over and select different platforms.",
            )
            # Reset to platform selection
            self.state_manager.set_state(client_id, WorkflowState.PLATFORM_SELECTION)
            # Send platform options again
            from app.services.workflow.handlers.platform_selection import PlatformSelectionHandler

            platform_handler = PlatformSelectionHandler(self.client, self.state_manager)
            await platform_handler.send_platform_options(client_id)
            return

        # Create buttons for each content type
        buttons = []
        for content_type in content_types:
            buttons.append({"id": content_type, "title": content_type.capitalize()})

        # Send interactive buttons (will automatically use list if > 3 buttons)
        await self.client.send_interactive_buttons(
            header_text=f"{platform.capitalize()} Content",
            body_text=f"Select a content type for {platform.capitalize()}:",
            buttons=buttons,
            phone_number=client_id,
        )
