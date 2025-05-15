from typing import Dict, Any, List, Optional, Tuple
from app.constants import _TEMPLATE_DATA


class TemplateManager:
    """Centralized manager for accessing and manipulating content templates"""

    def __init__(self):
        """Initialize with templates dictionary"""
        self.templates = _TEMPLATE_DATA

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template details by ID"""
        return self.templates.get(template_id)

    def get_template_type(self, template_id: str) -> Optional[str]:
        """Get the type of a template"""
        template = self.get_template(template_id)
        if not template:
            return None
        return template.get("type")

    def get_required_keys(self, template_id: str) -> List[str]:
        """Get the required keys for a template"""
        template = self.get_template(template_id)
        if not template:
            return []
        return template.get("required_keys", [])

    def filter_by_type(self, template_type: str) -> List[str]:
        """Get all template IDs of a specific type"""
        return [
            template_id
            for template_id, details in self.templates.items()
            if details.get("type") == template_type
        ]

    def get_by_platform(self, platform: str) -> List[Dict[str, Any]]:
        """Get all templates available for a platform"""
        platform_templates = []
        for template_id, details in self.templates.items():
            if template_id.startswith(f"{platform}_"):
                platform_templates.append(
                    {
                        "id": template_id,
                        "type": details.get("type", ""),
                        "required_keys": details.get("required_keys", []),
                    }
                )
        return platform_templates

    def find_template(
        self, platform: str, content_type: str, client_id: str
    ) -> Optional[str]:
        """Find a template ID based on platform, content type and client ID"""
        # Create the template ID pattern
        template_pattern = f"{platform}_{client_id}_{content_type}"

        # Look for exact match
        if template_pattern in self.templates:
            return template_pattern

        # Look for matching templates by type
        for template_id, details in self.templates.items():
            if (
                template_id.startswith(f"{platform}_")
                and template_id.endswith(f"_{content_type}")
                and details["type"] == content_type
            ):
                return template_id

        # Fallback to any template of matching type
        for template_id, details in self.templates.items():
            if details["type"] == content_type:
                return template_id

        return None

    def validate_inputs(
        self, template_id: str, user_inputs: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate user inputs against template requirements"""
        try:
            template = self.get_template(template_id)
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
            return False, f"Validation error: {str(e)}", {}

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


template_manager = TemplateManager()
