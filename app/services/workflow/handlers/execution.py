import random
from app.services.messaging.state_manager import WorkflowState
from app.services.workflow.handlers.base import BaseHandler
from app.constants import MESSAGES
from app.services.common.types import WorkflowContext


class ExecutionHandler(BaseHandler):
    """Handler for post execution state"""

    async def handle_confirmation(self, client_id: str, message: str) -> None:
        """Handle confirmation"""
        if message in ["yes", "y"]:
            # Move to post execution
            self.state_manager.set_state(client_id, WorkflowState.POST_EXECUTION)
            await self.handle_execution(client_id, "")

        elif message in ["no", "n"]:
            # Reset the workflow
            self.state_manager.reset_client(client_id)
            await self.send_message(
                client_id, "Let's start over. Type 'Create Post' when you're ready."
            )

        else:
            await self.send_message(client_id, "Please reply with 'yes' or 'no'.")
            context = WorkflowContext(**self.state_manager.get_context(client_id))
            await self.send_confirmation_summary(client_id, context)

    async def handle(self, client_id: str, message: str) -> None:
        """Handle post execution"""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # In a real implementation, this would call APIs to post to each platform
        # For now, we'll simulate success/failure
        await self.send_message(client_id, "Posting to selected platforms...")

        # Simulate posting to each platform
        success_platforms = []
        failed_platforms = []

        for platform in context.selected_platforms:
            # Simulate 80% success rate
            if random.random() < 0.8:
                success_platforms.append(platform)
                if context.post_status is None:
                    context.post_status = {}
                context.post_status[platform] = True
            else:
                failed_platforms.append(platform)
                if context.post_status is None:
                    context.post_status = {}
                context.post_status[platform] = False

        self.state_manager.update_context(client_id, vars(context))

        # Send result message
        if success_platforms and not failed_platforms:
            # All platforms succeeded
            await self.send_message(
                client_id, MESSAGES["post_success"].format(platforms=", ".join(success_platforms))
            )
        elif success_platforms and failed_platforms:
            # Some platforms succeeded, some failed
            await self.send_message(
                client_id,
                MESSAGES["post_partial_success"].format(
                    success_platforms=", ".join(success_platforms),
                    failed_platforms=", ".join(failed_platforms),
                ),
            )
        else:
            # All platforms failed
            await self.send_message(client_id, MESSAGES["post_failure"])

        # Reset the workflow
        self.state_manager.reset_client(client_id)
        await self.send_message(
            client_id, "Type 'Create Post' when you're ready to create another post."
        )

    async def send_confirmation_summary(self, client_id: str, context: WorkflowContext) -> None:
        """Send confirmation summary to the client"""
        # Format platforms and content types
        platforms = ", ".join(context.selected_platforms)
        content_types = ", ".join([f"{p}: {t}" for p, t in context.content_types.items()])

        # Create summary message
        summary = MESSAGES["confirmation_summary"].format(
            platforms=platforms,
            content_types=content_types,
            schedule=context.schedule_time,
            caption=context.caption,
        )

        # Send the selected image with the summary
        await self.client.send_media(
            media_items=[{"type": "image", "url": context.selected_image, "caption": summary}],
            phone_number=client_id,
        )

        # Send confirmation buttons
        buttons = [{"id": "yes", "title": "Yes, Post It"}, {"id": "no", "title": "No, Start Over"}]

        await self.client.send_interactive_buttons(
            header_text="Confirmation",
            body_text="Is this correct?",
            buttons=buttons,
            phone_number=client_id,
        )
