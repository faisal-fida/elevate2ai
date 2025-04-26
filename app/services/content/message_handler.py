from __future__ import annotations
from typing import List, Dict
import asyncio
from dataclasses import dataclass
from app.services.messaging.whatsapp import WhatsApp
from app.services.messaging.state_manager import StateManager, WorkflowState
from .generator import ContentGenerator
from .switchboard_canvas import create_image
from app.constants import MESSAGES, SOCIAL_MEDIA_PLATFORMS
import logging


@dataclass
class WorkflowContext:
    # Original fields
    caption: str = ""
    image_urls: List[str] = None
    original_text: str = ""

    # New fields for social media posting workflow
    selected_platforms: List[str] = None
    content_types: Dict[str, str] = None
    same_content_across_platforms: bool = False
    schedule_time: str = ""
    platform_specific_captions: Dict[str, str] = None
    current_platform_index: int = 0
    post_status: Dict[str, bool] = None
    common_content_types: List[str] = None

    def __post_init__(self):
        if self.image_urls is None:
            self.image_urls = []
        if self.selected_platforms is None:
            self.selected_platforms = []
        if self.content_types is None:
            self.content_types = {}
        if self.platform_specific_captions is None:
            self.platform_specific_captions = {}
        if self.post_status is None:
            self.post_status = {}


class MessageHandler:
    def __init__(
        self, whatsapp: WhatsApp, state_manager: StateManager, content_generator: ContentGenerator
    ):
        self.whatsapp = whatsapp
        self.state_manager = state_manager
        self.content_generator = content_generator
        self.logging = logging.getLogger(__name__)

    async def _send_message(self, client_id: str, message: str) -> None:
        await self.whatsapp.send_message(phone_number=client_id, message=message)

    async def _generate_and_send_gallery(self, client_id: str, text: str) -> WorkflowContext:
        """Use caption and image URLs to create content and send it to the client."""
        media_items = []

        # Generate content using the ContentGenerator
        caption, image_urls = await self.content_generator.generate_content(text)
        context = WorkflowContext(caption=caption, image_urls=image_urls, original_text=text)
        await self._send_message(client_id, f"Here is the caption for the post: {caption}")
        await self._send_message(client_id, "Please select one of the images below:")

        # Send the media items as a gallery
        for idx, url in enumerate(image_urls, 1):
            media_items.append(
                {"type": "image", "url": url, "caption": f"Reply with {idx} to select this image."}
            )

        self.logging.info(f"Sending media items to {client_id}")
        await self.whatsapp.send_media(media_items=media_items, phone_number=client_id)
        await asyncio.sleep(1)
        await self._send_message(
            client_id,
            "Reply with the number (1-4) to select an image, or type 'regenerate' for a new set.",
        )
        return context

    async def handle_init(self, client_id: str, message: str) -> None:
        """Handle the initial message from the client."""
        if message == "hi":
            await self._send_message(client_id, MESSAGES["welcome"])
            self.state_manager.set_state(client_id, WorkflowState.WAITING_FOR_PROMO)
        else:
            await self._send_message(client_id, MESSAGES["start_prompt"])

    async def handle_promo_text(self, client_id: str, message: str) -> None:
        """Handle the promo text message from the client."""
        await self._send_message(client_id, MESSAGES["generating"])
        context = await self._generate_and_send_gallery(client_id, message)
        self.state_manager.set_context(client_id, vars(context))
        self.state_manager.set_state(client_id, WorkflowState.WAITING_FOR_APPROVAL)

    async def handle_approval(self, client_id: str, message: str) -> None:
        context = WorkflowContext(**self.state_manager.get_context(client_id))
        if message in {"regenerate", "n"}:
            await self._send_message(client_id, MESSAGES["regenerating"])
            new_context = await self._generate_and_send_gallery(client_id, context.original_text)
            self.state_manager.update_context(client_id, vars(new_context))
        elif message in {"1", "2", "3", "4"}:
            idx = int(message) - 1
            if 0 <= idx < len(context.image_urls):
                selected_url = context.image_urls[idx]
                await self.whatsapp.send_media(
                    media_items={"type": "image", "url": selected_url, "caption": context.caption},
                    phone_number=client_id,
                )
                await self._send_message(client_id, MESSAGES["finalized"])

                # Start the social media posting workflow
                await self._handle_platform_selection(client_id)
            else:
                await self._send_message(
                    client_id, "Invalid number. Please reply with 1, 2, 3, or 4."
                )
        else:
            await self._send_message(client_id, "Please reply with 1, 2, 3, 4, or 'regenerate'.")

    async def _handle_platform_selection(self, client_id: str) -> None:
        """Handle platform selection step."""
        # Create buttons for platform selection
        buttons = [
            {"id": "instagram", "title": "Instagram"},
            {"id": "linkedin", "title": "LinkedIn"},
            {"id": "tiktok", "title": "TikTok"},
        ]

        # Initialize context with empty selected platforms
        context = WorkflowContext()
        self.state_manager.set_context(client_id, vars(context))

        # Send interactive buttons
        await self.whatsapp.send_interactive_buttons(
            phone_number=client_id,
            header_text="Platform Selection",
            body_text=MESSAGES["platform_selection"],
            buttons=buttons,
        )

        # Add "Done" button for when user has selected all desired platforms
        await self.whatsapp.send_interactive_buttons(
            phone_number=client_id,
            header_text="Finish Selection",
            body_text="Select 'Done' when you've chosen all platforms",
            buttons=[{"id": "done", "title": "Done"}],
        )

        self.state_manager.set_state(client_id, WorkflowState.PLATFORM_SELECTION)

    async def handle_platform_selection(self, client_id: str, message: str) -> None:
        """Process platform selection response."""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if message.lower() in ["instagram", "linkedin", "tiktok"]:
            # Add platform to selected platforms if not already selected
            if message.lower() not in context.selected_platforms:
                context.selected_platforms.append(message.lower())
                self.state_manager.update_context(client_id, vars(context))

                # Send confirmation message
                platforms_str = ", ".join(context.selected_platforms)
                await self._send_message(
                    client_id, MESSAGES["platform_selection_done"].format(platforms=platforms_str)
                )
            else:
                await self._send_message(client_id, f"You've already selected {message}.")

        elif message.lower() == "done":
            # Check if at least one platform is selected
            if not context.selected_platforms:
                await self._send_message(client_id, "Please select at least one platform.")
                await self._handle_platform_selection(client_id)
                return

            # Move to content type selection
            await self._handle_content_type_common(client_id)
        else:
            await self._send_message(
                client_id,
                "Please select a platform (Instagram, LinkedIn, TikTok) or 'Done' when finished.",
            )

    async def _handle_content_type_common(self, client_id: str) -> None:
        """Check if platforms have common content types and ask if user wants to use same content."""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Find common content types across selected platforms
        common_content_types = set()
        first_platform = True

        for platform in context.selected_platforms:
            platform_content_types = set(
                SOCIAL_MEDIA_PLATFORMS.get(platform, {}).get("content_types", [])
            )

            if first_platform:
                common_content_types = platform_content_types
                first_platform = False
            else:
                common_content_types &= platform_content_types

        # Store common content types in context
        context.common_content_types = list(common_content_types)
        self.state_manager.update_context(client_id, vars(context))

        # If there are common content types and multiple platforms, ask if user wants to use same content
        if common_content_types and len(context.selected_platforms) > 1:
            buttons = [{"id": "yes", "title": "Yes"}, {"id": "no", "title": "No"}]

            await self.whatsapp.send_interactive_buttons(
                phone_number=client_id,
                header_text="Content Selection",
                body_text=MESSAGES["same_content_prompt"],
                buttons=buttons,
            )

            self.state_manager.set_state(client_id, WorkflowState.SAME_CONTENT_CONFIRMATION)
        else:
            # If no common content types or only one platform, go to platform-specific content selection
            context.current_platform_index = 0
            self.state_manager.update_context(client_id, vars(context))
            await self._handle_platform_specific_content(client_id)

    async def handle_same_content_confirmation(self, client_id: str, message: str) -> None:
        """Process response to whether user wants to use same content across platforms."""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if message.lower() == "yes":
            # User wants to use same content type for all platforms
            context.same_content_across_platforms = True
            self.state_manager.update_context(client_id, vars(context))

            # Show common content types as buttons
            common_types = getattr(context, "common_content_types", [])
            buttons = [
                {"id": content_type, "title": content_type.title()}
                for content_type in common_types[:3]
            ]

            await self.whatsapp.send_interactive_buttons(
                phone_number=client_id,
                header_text="Content Type",
                body_text=MESSAGES["content_type_selection"],
                buttons=buttons,
            )

            self.state_manager.set_state(client_id, WorkflowState.CONTENT_TYPE_SELECTION)
        elif message.lower() == "no":
            # User wants to select content type for each platform separately
            context.same_content_across_platforms = False
            context.current_platform_index = 0
            self.state_manager.update_context(client_id, vars(context))

            # Go to platform-specific content selection
            await self._handle_platform_specific_content(client_id)
        else:
            await self._send_message(client_id, "Please reply with 'Yes' or 'No'.")

    async def handle_content_type_selection(self, client_id: str, message: str) -> None:
        """Process content type selection for all platforms."""
        context = WorkflowContext(**self.state_manager.get_context(client_id))
        common_types = getattr(context, "common_content_types", [])

        if message.lower() in [ct.lower() for ct in common_types]:
            # Apply the selected content type to all platforms
            for platform in context.selected_platforms:
                context.content_types[platform] = message.lower()

            self.state_manager.update_context(client_id, vars(context))

            # Move to caption input
            await self._handle_caption_input(client_id)
        else:
            await self._send_message(
                client_id, f"Please select a valid content type: {', '.join(common_types)}"
            )

    async def _handle_platform_specific_content(self, client_id: str) -> None:
        """Handle content type selection for a specific platform."""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Check if we've processed all platforms
        if context.current_platform_index >= len(context.selected_platforms):
            # Move to caption input
            await self._handle_caption_input(client_id)
            return

        # Get current platform
        current_platform = context.selected_platforms[context.current_platform_index]

        # Get content types for current platform
        content_types = SOCIAL_MEDIA_PLATFORMS.get(current_platform, {}).get("content_types", [])

        # Create buttons for content types (max 3 buttons per message)
        buttons = [{"id": ct, "title": ct.title()} for ct in content_types[:3]]

        await self.whatsapp.send_interactive_buttons(
            phone_number=client_id,
            header_text=f"{current_platform.title()} Content",
            body_text=MESSAGES["platform_specific_content"].format(
                platform=current_platform.title()
            ),
            buttons=buttons,
        )

        self.state_manager.set_state(client_id, WorkflowState.PLATFORM_SPECIFIC_CONTENT)

    async def handle_platform_specific_content(self, client_id: str, message: str) -> None:
        """Process content type selection for a specific platform."""
        context = WorkflowContext(**self.state_manager.get_context(client_id))
        current_platform = context.selected_platforms[context.current_platform_index]
        content_types = SOCIAL_MEDIA_PLATFORMS.get(current_platform, {}).get("content_types", [])

        if message.lower() in [ct.lower() for ct in content_types]:
            # Store the selected content type for this platform
            context.content_types[current_platform] = message.lower()

            # Move to next platform
            context.current_platform_index += 1
            self.state_manager.update_context(client_id, vars(context))

            # Process next platform or move to caption input
            await self._handle_platform_specific_content(client_id)
        else:
            await self._send_message(
                client_id,
                f"Please select a valid content type for {current_platform}: {', '.join(content_types)}",
            )

    async def _handle_caption_input(self, client_id: str) -> None:
        """Handle caption input step."""
        await self._send_message(client_id, MESSAGES["caption_prompt"])
        self.state_manager.set_state(client_id, WorkflowState.CAPTION_INPUT)

    async def handle_caption_input(self, client_id: str, message: str) -> None:
        """Process caption input."""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Store the caption
        context.caption = message
        self.state_manager.update_context(client_id, vars(context))

        # Move to schedule selection
        await self._handle_schedule_selection(client_id)

    async def _handle_schedule_selection(self, client_id: str) -> None:
        """Handle schedule selection step."""
        buttons = [
            {"id": "post_now", "title": "Post Now"},
            {"id": "schedule_later", "title": "Schedule Later"},
        ]

        await self.whatsapp.send_interactive_buttons(
            phone_number=client_id,
            header_text="Schedule",
            body_text=MESSAGES["schedule_prompt"],
            buttons=buttons,
        )

        self.state_manager.set_state(client_id, WorkflowState.SCHEDULE_SELECTION)

    async def handle_schedule_selection(self, client_id: str, message: str) -> None:
        """Process schedule selection."""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        if message.lower() == "post_now":
            context.schedule_time = "Now"
            self.state_manager.update_context(client_id, vars(context))

            # Move to confirmation
            await self._handle_confirmation(client_id)
        elif message.lower() == "schedule_later":
            await self._send_message(
                client_id, "Please enter the date and time for your post (format: YYYY-MM-DD HH:MM)"
            )
            # Stay in the same state but expect a date-time input
        elif self._is_valid_datetime_format(message):
            context.schedule_time = message
            self.state_manager.update_context(client_id, vars(context))

            # Move to confirmation
            await self._handle_confirmation(client_id)
        else:
            await self._send_message(
                client_id,
                "Please select 'Post Now', 'Schedule Later', or enter a valid date and time (YYYY-MM-DD HH:MM).",
            )

    def _is_valid_datetime_format(self, datetime_str: str) -> bool:
        """Check if the string is in a valid datetime format (YYYY-MM-DD HH:MM)."""
        # This is a simple validation - in a real app, you'd want more robust validation
        parts = datetime_str.split(" ")
        if len(parts) != 2:
            return False

        date_part, time_part = parts
        date_segments = date_part.split("-")
        time_segments = time_part.split(":")

        return (
            len(date_segments) == 3
            and len(time_segments) == 2
            and all(seg.isdigit() for seg in date_segments)
            and all(seg.isdigit() for seg in time_segments)
        )

    async def _handle_confirmation(self, client_id: str) -> None:
        """Handle confirmation step."""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # Format platforms and content types for display
        platforms_str = ", ".join(p.title() for p in context.selected_platforms)
        content_types_str = ", ".join(
            f"{p.title()}: {t.title()}" for p, t in context.content_types.items()
        )

        # Create summary message
        summary = MESSAGES["confirmation_summary"].format(
            platforms=platforms_str,
            content_types=content_types_str,
            schedule=context.schedule_time,
            caption=context.caption,
        )

        # Send confirmation buttons
        buttons = [{"id": "confirm", "title": "Confirm"}, {"id": "edit", "title": "Edit"}]

        await self.whatsapp.send_interactive_buttons(
            phone_number=client_id, header_text="Confirmation", body_text=summary, buttons=buttons
        )

        self.state_manager.set_state(client_id, WorkflowState.CONFIRMATION)

    async def handle_confirmation(self, client_id: str, message: str) -> None:
        """Process confirmation response."""
        # We don't need to use the context here, but we'll keep the retrieval for consistency
        # and in case we need to use it in the future

        if message.lower() == "confirm":
            # Execute the post
            await self._handle_post_execution(client_id)
        elif message.lower() == "edit":
            # Restart the workflow
            await self._handle_platform_selection(client_id)
        else:
            await self._send_message(client_id, "Please reply with 'Confirm' or 'Edit'.")

    async def _handle_post_execution(self, client_id: str) -> None:
        """Handle post execution step."""
        context = WorkflowContext(**self.state_manager.get_context(client_id))

        # In a real implementation, this would call APIs to post to each platform
        # For now, we'll simulate success/failure

        # Simulate posting to each platform
        success_platforms = []
        failed_platforms = []

        for platform in context.selected_platforms:
            # Simulate 80% success rate
            import random

            if random.random() < 0.8:
                success_platforms.append(platform)
                context.post_status[platform] = True
            else:
                failed_platforms.append(platform)
                context.post_status[platform] = False

        self.state_manager.update_context(client_id, vars(context))

        # Send appropriate message based on results
        if len(success_platforms) == len(context.selected_platforms):
            # All platforms successful
            platforms_str = ", ".join(p.title() for p in success_platforms)
            await self._send_message(
                client_id, MESSAGES["post_success"].format(platforms=platforms_str)
            )
        elif success_platforms:
            # Some platforms successful
            success_str = ", ".join(p.title() for p in success_platforms)
            failed_str = ", ".join(p.title() for p in failed_platforms)
            await self._send_message(
                client_id,
                MESSAGES["post_partial_success"].format(
                    success_platforms=success_str, failed_platforms=failed_str
                ),
            )
        else:
            # All platforms failed
            await self._send_message(client_id, MESSAGES["post_failure"])

        # Reset state
        self.state_manager.reset_client(client_id)
        await self._send_message(client_id, MESSAGES["menu_prompt"])
