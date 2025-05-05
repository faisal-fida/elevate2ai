import asyncio
from app.services.messaging.state_manager import WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import MESSAGES
from app.services.common.types import WorkflowContext


class SchedulingHandler(BaseHandler):
    """Handler for schedule selection state"""

    async def handle(self, client_id: str, message: str) -> None:
        """Handle schedule selection"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if message in ["1", "2", "3", "4"]:
            # Store the selected image
            idx = int(message) - 1
            if 0 <= idx < len(context.image_urls):
                context.selected_image = context.image_urls[idx]
                self.state_manager.update_context(client_id, vars(context))

                # Send scheduling options
                await self.send_scheduling_options(client_id)
            else:
                await self.send_message(
                    client_id, "Please select a valid image number (1-4)."
                )

        elif message in ["now", "later", "tomorrow", "next week"]:
            # Store the schedule
            context.schedule_time = message
            self.state_manager.update_context(client_id, vars(context))

            # Move to confirmation
            self.state_manager.set_state(client_id, WorkflowState.CONFIRMATION)
            await self.send_confirmation_summary(client_id, context)
        else:
            await self.send_message(
                client_id, "Please select a valid scheduling option."
            )
            await self.send_scheduling_options(client_id)

    async def send_scheduling_options(self, client_id: str) -> None:
        """Send scheduling options to the client"""
        # Create buttons for scheduling options
        buttons = [
            {"id": "later", "title": "Later Today"},
            {"id": "tomorrow", "title": "Tomorrow"},
            {"id": "next week", "title": "Next Week"},
            {"id": "now", "title": "Post Now"},
        ]

        # Send message first to provide context
        await self.send_message(client_id, MESSAGES["schedule_prompt"])

        # Send interactive buttons (will automatically use list if > 3 buttons)
        await self.client.send_interactive_buttons(
            header_text="Schedule Selection",
            body_text="When would you like to schedule your post?",
            buttons=buttons,
            phone_number=client_id,
        )

    async def send_confirmation_summary(
        self, client_id: str, context: WorkflowContext
    ) -> None:
        """Send confirmation summary to the client"""
        # Format platforms and content type
        platforms = ", ".join(
            platform.capitalize() for platform in context.selected_platforms
        )

        # Create summary message
        summary = MESSAGES["confirmation_summary"].format(
            content_type=context.selected_content_type.capitalize(),
            platforms=platforms,
            schedule=context.schedule_time,
            caption=context.caption,
        )

        # Send the selected image with the summary
        if context.selected_image:
            await self.client.send_media(
                media_items=[
                    {"type": "image", "url": context.selected_image, "caption": summary}
                ],
                phone_number=client_id,
            )
        else:
            # If no image is selected, just send the summary as a message
            await self.send_message(client_id, summary)

        await asyncio.sleep(1)

        # Send confirmation buttons
        buttons = [
            {"id": "yes", "title": "Yes, Continue"},
            {"id": "no", "title": "No, Start Over"},
        ]

        await self.client.send_interactive_buttons(
            header_text="Confirmation",
            body_text=MESSAGES["editing_confirmation"],
            buttons=buttons,
            phone_number=client_id,
        )
