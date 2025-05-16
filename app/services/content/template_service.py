from typing import Dict, List, Any, Optional, Tuple
from app.services.types import WorkflowContext
from app.services.messaging.state_manager import WorkflowState
from app.logging import setup_logger
from app.constants import DEFAULT_TEMPLATE_CLIENT_ID
from app.services.content.template_config import (
    FieldSource,
    get_template_config,
    get_field_config,
    build_template_id,
    get_required_keys,
)


class TemplateService:
    """Service for handling template-specific operations"""

    def __init__(self):
        """Initialize the template service"""
        self.logger = setup_logger(__name__)

    def get_template_id(
        self,
        platform: str,
        content_type: str,
        client_id: str = DEFAULT_TEMPLATE_CLIENT_ID,
    ) -> str:
        """Get the template ID for a platform and content type"""
        return build_template_id(platform, content_type, client_id)

    def get_required_fields(self, platform: str, content_type: str) -> List[str]:
        """Get the required fields for a template"""
        return get_required_keys(platform, content_type)

    def get_missing_fields(
        self, platform: str, content_type: str, context: WorkflowContext
    ) -> List[str]:
        """Get the missing required fields for a template"""
        required_fields = self.get_required_fields(platform, content_type)
        missing_fields = []

        for field in required_fields:
            # First check if the field is in template_data
            if (
                context.template_data
                and field in context.template_data
                and context.template_data[field]
            ):
                continue

            # Then check if it exists in the context
            if hasattr(context, field) and getattr(context, field):
                continue

            # If we get here, the field is missing
            missing_fields.append(field)

            # Log for debugging
            self.logger.debug(f"Missing field for {platform}_{content_type}: {field}")

        return missing_fields

    def get_next_field_to_collect(
        self, platform: str, content_type: str, context: WorkflowContext
    ) -> Optional[Tuple[str, WorkflowState, str]]:
        """
        Get the next field that needs to be collected from the user.
        Returns a tuple of (field_name, workflow_state, prompt) or None if no fields need to be collected.
        """
        missing_fields = self.get_missing_fields(platform, content_type, context)

        # Process fields in a specific order of priority
        priority_order = [
            "destination_name",
            "event_name",
            "price_text",
            "main_image",
            "event_image",
            "video_background",
        ]

        # Sort missing fields by priority
        missing_fields.sort(
            key=lambda x: priority_order.index(x) if x in priority_order else 999
        )

        for field in missing_fields:
            field_config = get_field_config(platform, content_type, field)

            # Collect fields that should come from user input or AI generation with user input
            if field_config:
                if field_config.source == FieldSource.USER_INPUT:
                    # Get the workflow state for this field
                    if field_config.workflow_state:
                        workflow_state = getattr(
                            WorkflowState, field_config.workflow_state
                        )
                        return (
                            field,
                            workflow_state,
                            field_config.prompt or f"Please enter {field}:",
                        )
                # For AI-generated fields that need user input
                elif (
                    field_config.source == FieldSource.AI_GENERATED
                    and field_config.workflow_state
                ):
                    workflow_state = getattr(WorkflowState, field_config.workflow_state)
                    return (
                        field,
                        workflow_state,
                        field_config.prompt or f"Please enter information for {field}:",
                    )

        return None

    def prepare_template_data(
        self, platform: str, content_type: str, context: WorkflowContext
    ) -> Dict[str, Any]:
        """
        Prepare template data based on the context and template configuration.
        This centralizes the logic for populating template fields.
        """
        template_data = {}
        template_config = get_template_config(platform, content_type)

        if not template_config:
            self.logger.warning(
                f"No template configuration found for {platform}_{content_type}"
            )
            return template_data

        # Process each field based on its source
        for field_name, field_config in template_config.fields.items():
            # User input fields - get from context
            if field_config.source == FieldSource.USER_INPUT:
                if hasattr(context, field_name) and getattr(context, field_name):
                    template_data[field_name] = getattr(context, field_name)

            # AI generated fields - typically caption_text
            elif field_config.source == FieldSource.AI_GENERATED:
                if field_name == "caption_text" and context.caption:
                    template_data[field_name] = context.caption

            # External service fields - images and videos
            elif field_config.source == FieldSource.EXTERNAL_SERVICE:
                if field_name == "main_image" and context.selected_image:
                    template_data[field_name] = context.selected_image
                elif field_name == "video_background" and context.selected_video:
                    template_data[field_name] = context.selected_video

            # For USER_INPUT fields that are images or videos, also use the selected media
            elif field_config.source == FieldSource.USER_INPUT:
                # For image fields, use the selected image
                if field_name == "main_image" and context.selected_image:
                    self.logger.info(
                        f"Using selected_image for main_image: {context.selected_image[:50]}..."
                    )
                    template_data[field_name] = context.selected_image
                # For video fields, use the selected video
                elif field_name == "video_background" and context.selected_video:
                    template_data[field_name] = context.selected_video

            # Derived fields - calculated from other fields
            elif field_config.source == FieldSource.DERIVED:
                # Handle derived fields based on their dependencies
                pass

        if (
            "event_image" in template_config.fields
            and "event_image" not in template_data
            and context.selected_image
        ):
            template_data["event_image"] = context.selected_image

        return template_data

    def validate_template_data(
        self, platform: str, content_type: str, template_data: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate template data against the template configuration.
        Returns (is_valid, error_message, validated_data)
        """
        required_fields = self.get_required_fields(platform, content_type)

        # Check for missing required fields
        missing_fields = [
            field for field in required_fields if field not in template_data
        ]

        # Special handling for events templates - if main_image is missing but we're in events content type
        if "main_image" in missing_fields and content_type == "events":
            self.logger.warning(
                "Missing main_image for events template, will be handled by execution handler"
            )
            # Remove main_image from missing fields to allow validation to proceed
            missing_fields = [
                field for field in missing_fields if field != "main_image"
            ]

        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}", {}

        # Validate field values
        validated_data = {}
        for field, value in template_data.items():
            field_config = get_field_config(platform, content_type, field)

            if not field_config:
                # Pass through fields not in the configuration
                validated_data[field] = value
                continue

            # Validate based on field type
            if field.endswith("_name") and field_config.max_words:
                words = str(value).strip().split()
                if len(words) > field_config.max_words:
                    return (
                        False,
                        f"{field} must be {field_config.max_words} words or less",
                        {},
                    )
                validated_data[field] = " ".join(words)

            # Validate media URLs
            elif field in ["main_image", "event_image", "video_background"]:
                if not value or not isinstance(value, str):
                    return False, f"Invalid {field} URL", {}
                validated_data[field] = value

            # Pass through other values
            else:
                validated_data[field] = value

        return True, "", validated_data

    def build_payload(
        self, template_id: str, template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build a payload for the template"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Ensure all required keys are present
        required_keys = template.get("required_keys", [])
        for key in required_keys:
            if key not in template_data:
                raise ValueError(f"Missing required key: {key}")

        # Build payload based on template type
        template_type = template.get("type", "")
        payload = {
            "template_id": template_id,
            "template_type": template_type,
        }

        # Add all template data
        for key, value in template_data.items():
            payload[key] = value

        return payload

# Create a singleton instance
template_service = TemplateService()
