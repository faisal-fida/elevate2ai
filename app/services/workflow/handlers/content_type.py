from typing import List
from app.services.messaging.state_manager import WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import MESSAGES, SOCIAL_MEDIA_PLATFORMS
from app.services.types import WorkflowContext
from app.services.content.template_service import template_service
from app.services.content.template_config import build_template_id


class ContentTypeHandler(BaseHandler):
    """Handler for content type selection state"""

    async def handle(self, client_id: str, message: str) -> None:
        """Handle content type selection"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if message in context.common_content_types:
            if context.content_types is None:
                context.content_types = {}

            for platform in context.selected_platforms:
                context.content_types[platform] = message

            self.state_manager.update_context(client_id, vars(context))

            if len(context.selected_platforms) == 1:
                context.same_content_across_platforms = True
                self.state_manager.update_context(client_id, vars(context))

                # Set state to CAPTION_INPUT
                self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)

                # Check if we need to collect template-specific fields first
                if await self.check_template_fields(client_id, context):
                    return  # Template fields are being collected

                # If no template fields needed, send the caption prompt
                await self.send_message(client_id, MESSAGES["caption_prompt"])
            else:
                self.state_manager.set_state(
                    client_id, WorkflowState.SAME_CONTENT_CONFIRMATION
                )
                await self.send_same_content_confirmation(client_id)

        else:
            await self.send_message(client_id, "Please select a valid content type.")
            await self.send_content_type_options(
                client_id, context.common_content_types
            )

    async def handle_confirmation(self, client_id: str, message: str) -> None:
        """Handle same content confirmation"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if message in ["yes", "y"]:
            context.same_content_across_platforms = True
            self.state_manager.update_context(client_id, vars(context))

            # Set state to CAPTION_INPUT
            self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)

            # Check if we need to collect template-specific fields first
            if await self.check_template_fields(client_id, context):
                return  # Template fields are being collected

            # If no template fields needed, send the caption prompt
            await self.send_message(client_id, MESSAGES["caption_prompt"])

        elif message in ["no", "n"]:
            context.same_content_across_platforms = False
            context.current_platform_index = 0
            self.state_manager.update_context(client_id, vars(context))

            self.state_manager.set_state(
                client_id, WorkflowState.PLATFORM_SPECIFIC_CONTENT
            )
            await self.handle_platform_specific(client_id, "")

        else:
            await self.send_message(client_id, "Please reply with 'yes' or 'no'.")
            await self.send_same_content_confirmation(client_id)

    async def handle_platform_specific(self, client_id: str, message: str) -> None:
        """Handle platform-specific content selection"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if message and context.current_platform_index > 0:
            current_platform = context.selected_platforms[
                context.current_platform_index - 1
            ]
            platform_content_types = SOCIAL_MEDIA_PLATFORMS[current_platform][
                "content_types"
            ]

            if message in platform_content_types:
                if context.content_types is None:
                    context.content_types = {}

                context.content_types[current_platform] = message
                self.state_manager.update_context(client_id, vars(context))
            else:
                await self.send_message(
                    client_id, "Please select a valid content type."
                )
                await self.send_platform_content_types(
                    client_id,
                    current_platform,
                    SOCIAL_MEDIA_PLATFORMS[current_platform]["content_types"],
                )
                return

        if context.current_platform_index < len(context.selected_platforms):
            current_platform = context.selected_platforms[
                context.current_platform_index
            ]
            context.current_platform_index += 1
            self.state_manager.update_context(client_id, vars(context))

            await self.send_platform_content_types(
                client_id,
                current_platform,
                SOCIAL_MEDIA_PLATFORMS[current_platform]["content_types"],
            )
        else:
            # Set state to CAPTION_INPUT
            self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)

            # Check if we need to collect template-specific fields first
            if await self.check_template_fields(client_id, context):
                return  # Template fields are being collected

            # If no template fields needed, send the caption prompt
            await self.send_message(client_id, MESSAGES["caption_prompt"])

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
            from app.services.workflow.handlers.platform_selection import (
                PlatformSelectionHandler,
            )

            platform_handler = PlatformSelectionHandler(self.client, self.state_manager)
            await platform_handler.send_platform_options(client_id)
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

    async def send_same_content_confirmation(self, client_id: str) -> None:
        """Send same content confirmation to the client"""
        buttons = [{"id": "yes", "title": "Yes"}, {"id": "no", "title": "No"}]

        await self.client.send_interactive_buttons(
            header_text="Content Confirmation",
            body_text=MESSAGES["same_content_prompt"],
            buttons=buttons,
            phone_number=client_id,
        )

    async def check_template_fields(
        self, client_id: str, context: WorkflowContext
    ) -> bool:
        """Check if template-specific fields need to be collected"""
        if not context.content_types:
            return False

        for platform, content_type in context.content_types.items():
            # Build template ID
            template_id = build_template_id(platform, content_type, client_id)
            context.template_id = template_id
            self.state_manager.update_context(client_id, vars(context))

            # Get next field to collect
            next_field = template_service.get_next_field_to_collect(
                platform, content_type, context
            )

            if next_field:
                field_name, workflow_state, prompt = next_field
                self.state_manager.set_state(client_id, workflow_state)
                await self.send_message(client_id, prompt)
                return True

            # Validate field dependencies
            is_valid, error_message = template_service.validate_field_dependencies(
                platform, content_type, context
            )
            if not is_valid:
                self.logger.warning(
                    f"Field dependency validation failed: {error_message}"
                )
                await self.send_message(
                    client_id,
                    f"There was an issue with the template fields: {error_message}",
                )
                return True

        return False

    async def send_platform_content_types(
        self, client_id: str, platform: str, content_types: List[str]
    ) -> None:
        """Send platform-specific content types to the client"""
        await self.send_message(
            client_id,
            MESSAGES["platform_specific_content"].format(
                platform=platform.capitalize()
            ),
        )

        if not content_types:
            await self.send_message(
                client_id,
                f"No content types available for {platform.capitalize()}. Please start over and select different platforms.",
            )
            self.state_manager.set_state(client_id, WorkflowState.PLATFORM_SELECTION)
            from app.services.workflow.handlers.platform_selection import (
                PlatformSelectionHandler,
            )

            platform_handler = PlatformSelectionHandler(self.client, self.state_manager)
            await platform_handler.send_platform_options(client_id)
            return

        buttons = []
        for content_type in content_types:
            buttons.append({"id": content_type, "title": content_type.capitalize()})

        await self.client.send_interactive_buttons(
            header_text=f"{platform.capitalize()} Content",
            body_text=f"Select a content type for {platform.capitalize()}:",
            buttons=buttons,
            phone_number=client_id,
        )
