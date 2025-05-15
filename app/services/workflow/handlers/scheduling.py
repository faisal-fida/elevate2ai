import asyncio
from app.services.messaging.state_manager import WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import MESSAGES
from app.services.common.types import WorkflowContext


class SchedulingHandler(BaseHandler):
    """Handler for schedule selection state"""

    async def handle(self, client_id: str, message: str) -> None:
        """Handle scheduling selection"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if message.lower() in ["1", "now", "post now"]:
            context.schedule_time = "now"
            self.state_manager.update_context(client_id, context.model_dump())
            self.state_manager.set_state(client_id, WorkflowState.CONFIRMATION)
            await self.send_confirmation_summary(client_id, context)

        elif message.lower() in ["2", "later", "later today"]:
            context.schedule_time = "later today"
            self.state_manager.update_context(client_id, context.model_dump())
            self.state_manager.set_state(client_id, WorkflowState.CONFIRMATION)
            await self.send_confirmation_summary(client_id, context)

        elif message.lower() in ["3", "tomorrow"]:
            context.schedule_time = "tomorrow"
            self.state_manager.update_context(client_id, context.model_dump())
            self.state_manager.set_state(client_id, WorkflowState.CONFIRMATION)
            await self.send_confirmation_summary(client_id, context)

        elif message.lower() in ["4", "next week"]:
            context.schedule_time = "next week"
            self.state_manager.update_context(client_id, context.model_dump())
            self.state_manager.set_state(client_id, WorkflowState.CONFIRMATION)
            await self.send_confirmation_summary(client_id, context)

        else:
            await self.send_message(
                client_id,
                "Please select a valid scheduling option: 'now', 'later today', 'tomorrow', or 'next week'.",
            )
            await self.send_scheduling_options(client_id)

    async def send_scheduling_options(self, client_id: str) -> None:
        """Send scheduling options to the client"""
        buttons = [
            {"id": "later", "title": "Later Today"},
            {"id": "tomorrow", "title": "Tomorrow"},
            {"id": "next week", "title": "Next Week"},
            {"id": "now", "title": "Post Now"},
        ]

        await self.send_message(client_id, MESSAGES["schedule_prompt"])
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
        platforms = ", ".join(
            platform.capitalize() for platform in context.selected_platforms
        )

        summary = MESSAGES["confirmation_summary"].format(
            content_type=context.selected_content_type.capitalize(),
            platforms=platforms,
            schedule=context.schedule_time,
            caption=context.caption,
        )

        include_images = getattr(context, "include_images", True)
        if include_images and context.selected_image:
            await self.client.send_media(
                media_items=[
                    {"type": "image", "url": context.selected_image, "caption": summary}
                ],
                phone_number=client_id,
            )
        else:
            await self.send_message(client_id, summary)

        await asyncio.sleep(1)
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
