from typing import Dict, List, Any, Optional, Tuple
from app.constants import TEMPLATE_CONFIG
from app.services.common.logging import setup_logger

logger = setup_logger(__name__)


def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    """Get template details by ID."""

    return TEMPLATE_CONFIG["templates"].get(template_id)


def get_required_keys(template_id: str) -> List[str]:
    """Get the required keys for a template."""

    template = get_template_by_id(template_id)
    if not template:
        return []
    return template.get("required_keys", [])


def get_template_type(template_id: str) -> Optional[str]:
    """Get the type of a template."""

    template = get_template_by_id(template_id)
    if not template:
        return None
    return template.get("type")


def filter_templates_by_type(template_type: str) -> List[str]:
    """Get all template IDs of a specific type."""

    return [
        template_id
        for template_id, details in TEMPLATE_CONFIG["templates"].items()
        if details.get("type") == template_type
    ]


def validate_template_inputs(
    template_id: str, user_inputs: Dict[str, Any]
) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate user inputs against template requirements."""

    try:
        template = get_template_by_id(template_id)
        if not template:
            return False, f"Template {template_id} not found", {}

        required_keys = template.get("required_keys", [])

        # Check for missing required keys
        missing_keys = [key for key in required_keys if key not in user_inputs]
        if missing_keys:
            return False, f"Missing required keys: {', '.join(missing_keys)}", {}

        # Validate input values
        validated_inputs = {}
        for key, value in user_inputs.items():
            # Validate name inputs
            if key.endswith("_name"):
                words = str(value).strip().split()
                if len(words) > 5:
                    return False, f"{key} must be 5 words or less", {}
                validated_inputs[key] = " ".join(words)
            # Validate media URLs
            elif key in ["main_image", "event_image", "video_background"]:
                if not value or not isinstance(value, str):
                    return False, f"Invalid {key} URL", {}
                validated_inputs[key] = value
            # Pass through other values
            else:
                validated_inputs[key] = value

        return True, "", validated_inputs

    except Exception as e:
        logger.error(f"Error validating template inputs: {e}")
        return False, f"Validation error: {str(e)}", {}


def get_templates_for_platform(platform: str) -> List[Dict[str, Any]]:
    """Get all templates available for a platform."""

    platform_templates = []
    for template_id, details in TEMPLATE_CONFIG["templates"].items():
        if template_id.startswith(f"{platform}_"):
            platform_templates.append(
                {
                    "id": template_id,
                    "type": details.get("type", ""),
                    "required_keys": details.get("required_keys", []),
                }
            )
    return platform_templates


def build_template_payload(
    template_id: str, template_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Build a payload for the template."""

    template = get_template_by_id(template_id)
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
