import httpx
from typing import Dict, List, Any
from app.config import settings
from app.constants import SOCIAL_MEDIA_PLATFORMS, TEMPLATE_CONFIG
from app.services.common.logging import setup_logger


class SwitchboardCanvas:
    """Service for interacting with Switchboard Canvas API"""

    def __init__(self, base_url: str = "https://api.canvas.switchboard.ai"):
        self.api_key = settings.SWITCHBOARD_API_KEY
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        self.logger = setup_logger(__name__)
        # Create a single client instance for reuse
        self.client = httpx.Client(timeout=30.0, headers=self.headers, verify=True)

    def __del__(self):
        """Ensure client is closed when the instance is destroyed"""
        if self.client:
            self.logger.debug("Closing HTTP client")
            try:
                self.client.close()
            except Exception as e:
                self.logger.error(f"Error closing HTTP client: {e}")
        else:
            self.logger.debug("Client already closed or not initialized")

    def get_template_elements(self, template: str) -> List[Dict[str, Any]]:
        """Fetches the elements defined in a given template."""
        url = f"{self.base_url}/template/{template}/elements"
        try:
            self.logger.info(f"Fetching template elements for {template}")
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("fields", [])
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error fetching template elements: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error fetching template elements: {e}")
            raise

    def validate_template_data(
        self, template_id: str, template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validates that all required keys for a template are provided.
        Returns the validated data or raises ValueError.
        """
        # Get template configuration
        template_config = TEMPLATE_CONFIG["templates"].get(template_id)
        if not template_config:
            raise ValueError(f"Template {template_id} not found in configuration")

        required_keys = template_config.get("required_keys", [])

        # Check if all required keys are present
        missing_keys = [key for key in required_keys if key not in template_data]
        if missing_keys:
            raise ValueError(
                f"Missing required keys for template {template_id}: {', '.join(missing_keys)}"
            )

        # Validate media assets
        for key in required_keys:
            if key in ["main_image", "event_image", "video_background"]:
                if not template_data.get(key):
                    raise ValueError(f"Missing or invalid {key} URL")

        # Apply any template-specific validations
        template_type = template_config.get("type")
        if template_type == "destination" and "destination_name" in required_keys:
            if len(template_data.get("destination_name", "").split()) > 5:
                raise ValueError("Destination name should be 5 words or less")

        if template_type == "events" and "event_name" in required_keys:
            if len(template_data.get("event_name", "").split()) > 5:
                raise ValueError("Event name should be 5 words or less")

        return template_data

    def get_payload(
        self,
        client_id: str,
        template_data: Dict[str, Any],
        platform: str,
        post_type: str,
    ) -> Dict[str, Any]:
        """Create a payload for the Switchboard Canvas API"""
        try:
            template_name = f"{platform.lower()}_{client_id}_{post_type.lower()}"
            elements = self.get_template_elements(template_name)
            self.logger.info(f"Elements: {elements}")

            # Validate the template data
            validated_data = self.validate_template_data(template_name, template_data)

            payload_elements = {}

            # Construct payload based on the template elements
            for element in elements:
                element_name = element["name"]

                # Handle media assets (images/videos)
                if (
                    element_name in ["main_image", "event_image"]
                    and element_name in validated_data
                ):
                    payload_elements[element_name] = {
                        "url": validated_data[element_name]
                    }

                # Handle video backgrounds
                elif (
                    element_name == "video_background"
                    and element_name in validated_data
                ):
                    payload_elements[element_name] = {
                        "url": validated_data[element_name]
                    }

                # Handle text elements
                elif element_name in [
                    "headline_text",
                    "caption_text",
                    "price_text",
                    "destination_name",
                    "event_name",
                ]:
                    if element_name in validated_data:
                        payload_elements[element_name] = {
                            "text": validated_data[element_name]
                        }

                # Always include the logo if it's a required element
                elif element_name == "logo":
                    # In a production environment, this would fetch from a database
                    # For now, use a placeholder
                    payload_elements[element_name] = {
                        "url": "https://onlinepngtools.com/images/examples-onlinepngtools/google-logo-transparent.png"
                    }

            # Get platform-specific image sizes
            platform_sizes = SOCIAL_MEDIA_PLATFORMS.get(platform, {}).get("sizes", [])
            if not platform_sizes:
                self.logger.warning(
                    f"No sizes found for platform {platform}, using default"
                )
                platform_sizes = [{"width": 1080, "height": 1080}]  # Default to square

            payload = {
                "template": template_name,
                "sizes": platform_sizes,
                "elements": payload_elements,
            }

            self.logger.info(f"Created payload for {template_name}")
            return payload
        except Exception as e:
            self.logger.error(f"Error creating payload: {e}")
            raise

    def generate_image(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an image using the Switchboard Canvas API"""
        try:
            self.logger.info("Generating image with Switchboard Canvas")
            response = self.client.post(self.base_url, json=payload)
            self.logger.debug(f"Switchboard API response: {response.text}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error generating image: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error generating image: {e}")
            raise


def create_image(
    client_id: str,
    template_data: Dict[str, Any],
    platform: str,
    post_type: str,
) -> Dict[str, Any]:
    """Helper function to create an image using Switchboard Canvas

    Args:
        client_id: The client's ID
        template_data: Dictionary containing template data including media URLs and text
        platform: The social media platform (instagram, linkedin, tiktok)
        post_type: The type of content (destination, events, etc.)

    Returns:
        Response from Switchboard Canvas API
    """
    canvas = SwitchboardCanvas()
    payload = canvas.get_payload(client_id, template_data, platform, post_type)
    response = canvas.generate_image(payload)
    return response
