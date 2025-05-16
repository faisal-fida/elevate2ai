from typing import List
from app.services.messaging.state_manager import WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import MESSAGES, DEFAULT_TEMPLATE_CLIENT_ID
from app.services.types import WorkflowContext
from app.services.content.template_service import template_service
from app.services.content.template_config import build_template_id


class PlatformSelectionForContentHandler(BaseHandler):
    """Handler for platform selection for a specific content type"""

    async def handle(self, client_id: str, message: str) -> None:
        """Handle platform selection for content type"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if message == "all":
            context.selected_platforms = context.supported_platforms.copy()
            for platform in context.selected_platforms:
                context.content_types[platform] = context.selected_content_type

            self.state_manager.update_context(client_id, context.model_dump())
            platforms_str = ", ".join(
                platform.capitalize() for platform in context.selected_platforms
            )
            await self.send_message(
                client_id, f"You've selected all platforms: {platforms_str}"
            )

            # Set state to CAPTION_INPUT
            self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)

            # Check if we need to collect template-specific fields first
            if await self.check_template_fields(client_id, context):
                return  # Template fields are being collected

            # If no template fields needed, send the caption prompt
            await self.send_message(client_id, MESSAGES["caption_prompt"])
        elif message in context.supported_platforms:
            if message not in context.selected_platforms:
                context.selected_platforms.append(message)
                context.content_types[message] = context.selected_content_type
                self.state_manager.update_context(client_id, context.model_dump())
                await self.send_message(
                    client_id, f"Added {message} to your selected platforms."
                )
            else:
                await self.send_message(
                    client_id, f"You've already selected {message}."
                )

            await self.ask_add_more_platforms(client_id)
        elif message in ["done", "no", "n", "finished"]:
            if not context.selected_platforms:
                await self.send_message(
                    client_id, "Please select at least one platform before proceeding."
                )
                await self.send_platform_options(
                    client_id,
                    context.selected_content_type,
                    context.supported_platforms,
                )
                return

            # Set state to CAPTION_INPUT
            self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)

            # Check if we need to collect template-specific fields first
            if await self.check_template_fields(client_id, context):
                return  # Template fields are being collected

            # If no template fields needed, send the caption prompt
            await self.send_message(client_id, MESSAGES["caption_prompt"])
        else:
            await self.send_message(
                client_id,
                f"Sorry, '{message}' is not a valid platform for {context.selected_content_type} content.",
            )
            await self.send_platform_options(
                client_id, context.selected_content_type, context.supported_platforms
            )

    async def ask_add_more_platforms(self, client_id: str) -> None:
        """Ask if the user wants to add more platforms"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        remaining_platforms = [
            p
            for p in context.supported_platforms
            if p not in context.selected_platforms
        ]

        if remaining_platforms:
            buttons = [
                {"id": platform, "title": platform.capitalize()}
                for platform in remaining_platforms
            ]

            buttons.append({"id": "done", "title": "Done"})

            try:
                await self.client.send_interactive_buttons(
                    header_text="Platform Selection",
                    body_text=f"Would you like to add more platforms? Currently selected: {', '.join(context.selected_platforms)}",
                    buttons=buttons,
                    phone_number=client_id,
                )
            except Exception as e:
                self.logger.error(f"Error sending interactive buttons: {e}")
                platforms_text = "\n".join(
                    [f"- {p.capitalize()}" for p in remaining_platforms]
                )
                await self.send_message(
                    client_id,
                    f"Would you like to add more platforms? Currently selected: {', '.join(context.selected_platforms)}\n\nAvailable platforms:\n{platforms_text}\n\nReply with a platform name or 'done' to continue.",
                )
        else:
            # Set state to CAPTION_INPUT
            self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)

            # Check if we need to collect template-specific fields first
            if await self.check_template_fields(client_id, context):
                return  # Template fields are being collected

            # If no template fields needed, send the caption prompt
            await self.send_message(
                client_id,
                f"All platforms selected: {', '.join(context.selected_platforms)}. {MESSAGES['caption_prompt']}",
            )

    async def check_template_fields(
        self, client_id: str, context: WorkflowContext
    ) -> bool:
        """
        Check if we need to collect template-specific fields first.
        Returns True if template fields are being collected.
        """
        # Find template if not already set
        if (
            not context.template_id
            and context.selected_platforms
            and context.selected_content_type
        ):
            platform = context.selected_platforms[0]
            content_type = context.selected_content_type

            # Get the template ID
            template_id = build_template_id(
                platform=platform,
                content_type=content_type,
                client_id=DEFAULT_TEMPLATE_CLIENT_ID,
            )

            if template_id:
                context.template_id = template_id
                context.template_type = content_type
                self.state_manager.update_context(client_id, context.model_dump())

        # If we have a template ID, check for required fields
        if context.template_id:
            # Extract platform and content_type from template_id
            parts = context.template_id.split("_")
            if len(parts) >= 3:
                platform = parts[0]
                content_type = parts[2]

                # Use the template service to get the next field to collect
                next_field = template_service.get_next_field_to_collect(
                    platform=platform, content_type=content_type, context=context
                )

                if next_field:
                    field_name, workflow_state, prompt = next_field
                    self.logger.info(
                        f"Requesting field {field_name} for {platform}_{content_type}"
                    )

                    # Set the state and send the prompt
                    self.state_manager.set_state(client_id, workflow_state)
                    await self.send_message(client_id, prompt)
                    return True

        return False  # No template fields needed

    async def send_platform_options(
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
