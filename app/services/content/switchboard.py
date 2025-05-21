import httpx
from typing import Dict, Any
from app.constants import SOCIAL_MEDIA_PLATFORMS
from app.config import settings
from app.logging import setup_logger

from app.services.content.template_config import get_template_config
from app.services.content.template_service import template_service


class SwitchboardService:
    """Service for interacting with Switchboard Canvas API"""

    def __init__(self, base_url: str = "https://api.canvas.switchboard.ai"):
        self.base_url = base_url.rstrip("/")
        self.logger = setup_logger(__name__)
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "X-API-Key": settings.SWITCHBOARD_API_KEY,
                "Content-Type": "application/json",
            },
            verify=True,
        )

    def build_payload(
        self,
        client_id: str,
        template_data: Dict[str, Any],
        platform: str,
        post_type: str,
    ) -> Dict[str, Any]:
        """Create a payload for the Switchboard Canvas API"""

        # Get the template configuration
        template_id = f"{platform.lower()}_{client_id}_{post_type.lower()}"
        template_config = get_template_config(platform, post_type)
        if not template_config:
            raise ValueError(f"Template {template_id} not found in configuration")

        # Filter template_data to include only required keys
        required_keys = template_service.get_required_fields(platform, post_type)

        #! TODO: remove this once we have a real logo
        required_keys.append("logo")
        template_data["logo"] = (
            "https://cdn.freebiesupply.com/logos/thumbs/2x/star-wars-logo.png"
        )

        filtered_elements = {
            key: {"url": value}
            if key in ["main_image", "event_image", "video_background", "logo"]
            else {"text": value}
            for key, value in template_data.items()
            if key in required_keys
        }

        # Check for missing required keys
        missing_keys = [key for key in required_keys if key not in template_data]
        if missing_keys:
            raise ValueError(
                f"Missing required keys for template {template_id}: {', '.join(missing_keys)}"
            )

        # Build the payload
        platform_sizes = SOCIAL_MEDIA_PLATFORMS.get(platform, {}).get(
            "sizes", [{"width": 1080, "height": 1080}]
        )
        return {
            "template": template_id,
            "sizes": platform_sizes,
            "elements": filtered_elements,
        }

    def edit_media(
        self,
        client_id: str,
        template_data: Dict[str, Any],
        platform: str,
        post_type: str,
    ) -> Dict[str, Any]:
        """Helper function to create an image using Switchboard Canvas"""
        try:
            for key in ["main_image", "event_image", "video_background", "logo"]:
                val = template_data.get(key)
                if isinstance(val, str) and val.startswith("/"):
                    #! TODO: replace with a real external URL: template_data[key] = f"{MEDIA_BASE_URL}{url}"
                    template_data[key] = (
                        "https://images.unsplash.com/photo-1454496522488-7a8e488e8606"
                    )

            self.logger.info(f"Editing image with template data: {template_data}")
            payload = self.build_payload(client_id, template_data, platform, post_type)
            self.logger.info(f"Successfully built payload: {payload}")
            response = self.client.post(self.base_url, json=payload)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            self.logger.error(
                f"Error editing image | Payload: {payload} | Response: {response.text} | Error: {e}"
            )
            return None


switchboard_service = SwitchboardService()
