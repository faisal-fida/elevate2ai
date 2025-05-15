import httpx
from typing import Dict, Any
from app.constants import SOCIAL_MEDIA_PLATFORMS, template_manager
from app.config import settings
from app.services.common.logging import setup_logger


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
        template_config = template_manager.get_template(template_id)
        if not template_config:
            raise ValueError(f"Template {template_id} not found in configuration")

        # Filter template_data to include only required keys
        required_keys = template_config.get("required_keys", [])
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

        for key in ["main_image", "event_image", "video_background", "logo"]:
            val = template_data.get(key)
            if isinstance(val, str) and val.startswith("/"):
                #! TODO: replace with a real external URL: template_data[key] = f"{MEDIA_BASE_URL}{url}"
                template_data[key] = (
                    "https://images.unsplash.com/photo-1454496522488-7a8e488e8606"
                )
        client_id = "351915950259"  #! TODO: remove this hardcoding
        self.logger.info(f"Editing image with template data: {template_data}")
        payload = self.build_payload(client_id, template_data, platform, post_type)
        response = self.client.post(self.base_url, json=payload)
        response.raise_for_status()
        self.logger.info(f"Successfully edited image with payload: {payload}")
        return response.json()
