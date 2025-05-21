from typing import Dict, List, Any, Optional, Tuple
from app.services.types import WorkflowContext
from app.services.messaging.state_manager import WorkflowState
from app.logging import setup_logger
from app.constants import DEFAULT_TEMPLATE_CLIENT_ID
from app.services.content.template_config import (
    FieldSource,
    get_template_config,
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
        template_config = get_template_config(platform, content_type)

        if not template_config:
            self.logger.warning(
                f"No template configuration found for {platform}_{content_type}"
            )
            return None

        # Sort fields based on dependencies and source type
        def get_field_priority(field_name: str) -> int:
            field_config = template_config.fields.get(field_name)
            if not field_config:
                return 999

            # User input fields come first
            if field_config.source == FieldSource.USER_INPUT:
                return 0
            # Then AI-generated fields that need user input
            elif (
                field_config.source == FieldSource.AI_GENERATED
                and field_config.workflow_state
            ):
                return 1
            # Then external service fields
            elif field_config.source == FieldSource.EXTERNAL_SERVICE:
                return 2
            # Then derived fields
            elif field_config.source == FieldSource.DERIVED:
                return 3
            return 999

        # Sort missing fields by priority
        missing_fields.sort(key=get_field_priority)

        for field in missing_fields:
            field_config = template_config.fields.get(field)
            if not field_config:
                continue

            # Handle user input fields
            if field_config.source == FieldSource.USER_INPUT:
                if field_config.workflow_state:
                    workflow_state = getattr(WorkflowState, field_config.workflow_state)
                    return (
                        field,
                        workflow_state,
                        field_config.prompt or f"Please enter {field}:",
                    )

            # Handle AI-generated fields that need user input
            elif (
                field_config.source == FieldSource.AI_GENERATED
                and field_config.workflow_state
            ):
                # Check if we have all dependencies
                if all(dep in context.template_data for dep in field_config.depends_on):
                    workflow_state = getattr(WorkflowState, field_config.workflow_state)
                    return (
                        field,
                        workflow_state,
                        field_config.prompt or f"Please enter information for {field}:",
                    )

            # Handle external service fields that need user input
            elif (
                field_config.source == FieldSource.EXTERNAL_SERVICE
                and field_config.workflow_state
            ):
                workflow_state = getattr(WorkflowState, field_config.workflow_state)
                return (
                    field,
                    workflow_state,
                    field_config.prompt or f"Please provide {field}:",
                )

        return None

    def prepare_template_data(
        self, platform: str, content_type: str, context: WorkflowContext
    ) -> Dict[str, Any]:
        """
        Prepare template data based on the context and template configuration.
        This centralizes the logic for populating template fields.
        """
        # Start with existing template data if available
        template_data = context.template_data.copy() if context.template_data else {}

        template_config = get_template_config(platform, content_type)
        if not template_config:
            self.logger.warning(
                f"No template configuration found for {platform}_{content_type}"
            )
            return template_data

        # Process each field based on its source
        for field_name, field_config in template_config.fields.items():
            # Skip if field is already in template_data and has a value
            if field_name in template_data and template_data[field_name]:
                continue

            # User input fields - get from context
            if field_config.source == FieldSource.USER_INPUT:
                # Check context attributes first
                if hasattr(context, field_name) and getattr(context, field_name):
                    template_data[field_name] = getattr(context, field_name)
                # For media fields, check selected media
                elif field_name == "main_image" and context.selected_image:
                    template_data[field_name] = context.selected_image
                elif field_name == "video_background" and context.selected_video:
                    template_data[field_name] = context.selected_video

            # AI generated fields - typically caption_text
            elif field_config.source == FieldSource.AI_GENERATED:
                if field_name == "caption_text" and context.caption:
                    template_data[field_name] = context.caption
                elif hasattr(context, field_name) and getattr(context, field_name):
                    template_data[field_name] = getattr(context, field_name)

            # External service fields - images and videos
            elif field_config.source == FieldSource.EXTERNAL_SERVICE:
                if field_name == "main_image":
                    # Try context.selected_image first, then context.main_image
                    if context.selected_image:
                        template_data[field_name] = context.selected_image
                    elif context.main_image:
                        template_data[field_name] = context.main_image
                elif field_name == "video_background":
                    # Try context.selected_video first, then context.video_background
                    if context.selected_video:
                        template_data[field_name] = context.selected_video
                    elif context.video_background:
                        template_data[field_name] = context.video_background

            # Derived fields - calculated from other fields
            elif field_config.source == FieldSource.DERIVED:
                # Handle derived fields based on their dependencies
                if all(dep in template_data for dep in field_config.depends_on):
                    # TODO: Implement derived field logic
                    pass

        # Log the prepared template data
        self.logger.info(
            f"Prepared template data for {platform}_{content_type}: {template_data}"
        )

        return template_data

    def validate_template_data(
        self, platform: str, content_type: str, template_data: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate template data against the template configuration.
        Returns (is_valid, error_message, validated_data)
        """
        try:
            # Get template configuration
            template_config = get_template_config(platform, content_type)
            if not template_config:
                return (
                    False,
                    f"No template configuration found for {platform}_{content_type}",
                    {},
                )

            # Track missing and invalid fields
            missing_fields = []
            invalid_fields = []
            validated_data = {}

            # Check each required field
            for field_name, field_config in template_config.fields.items():
                if not field_config.required:
                    continue

                # Check if field is present
                if field_name not in template_data:
                    missing_fields.append(field_name)
                    continue

                value = template_data[field_name]

                # Validate field value
                if value is None or (isinstance(value, str) and not value.strip()):
                    missing_fields.append(field_name)
                    continue

                # Validate max words if specified
                if field_config.max_words and isinstance(value, str):
                    words = value.split()
                    if len(words) > field_config.max_words:
                        invalid_fields.append(
                            f"{field_name} exceeds {field_config.max_words} words"
                        )
                        continue

                # Add to validated data if all checks pass
                validated_data[field_name] = value

            # Build error message if any issues found
            if missing_fields or invalid_fields:
                error_parts = []
                if missing_fields:
                    error_parts.append(
                        f"Missing required fields: {', '.join(missing_fields)}"
                    )
                if invalid_fields:
                    error_parts.append(f"Invalid fields: {', '.join(invalid_fields)}")
                return False, "; ".join(error_parts), validated_data

            return True, "", validated_data

        except Exception as e:
            self.logger.error(f"Error validating template data: {str(e)}")
            return False, f"Error validating template data: {str(e)}", {}

    def build_payload(
        self, template_id: str, template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build a payload for the template"""

        # Get the template configuration
        # Template ID format is platform_client_id_content_type
        parts = template_id.split("_")
        if len(parts) < 3:
            raise ValueError(f"Invalid template ID format: {template_id}")

        platform = parts[0]
        content_type = parts[-1]  # Last part is always content_type
        template_config = get_template_config(platform, content_type)

        if not template_config:
            raise ValueError(f"Template {template_id} not found")

        # Ensure all required keys are present
        required_keys = template_service.get_required_fields(platform, content_type)
        for key in required_keys:
            if key not in template_data:
                raise ValueError(f"Missing required key: {key}")

        # Build payload based on template type
        template_type = template_config.type
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
