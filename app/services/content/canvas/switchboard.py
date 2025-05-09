import httpx
from typing import Dict, List, Any
from app.config import settings
from app.constants import SOCIAL_MEDIA_PLATFORMS
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
        self.client = httpx.Client(
            timeout=30.0, headers=self.headers, verify=True, http2=True
        )

    def __del__(self):
        """Ensure client is closed when the instance is destroyed"""
        self.client.close()

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

    def get_payload(
        self,
        client_id: str,
        selected_url: str,
        caption: str,
        platform: str,
        post_type: str,
    ) -> Dict[str, Any]:
        """Create a payload for the Switchboard Canvas API"""
        try:
            template_name = f"{platform.lower()}_{client_id}_{post_type.lower()}"
            elements = self.get_template_elements(template_name)
            self.logger.debug(f"Elements: {elements}")

            payload_elements = {}

            for element in elements:
                if element["name"] == "main_image":
                    payload_elements[element["name"]] = {"url": selected_url}
                elif element["name"] == "headline_text":
                    payload_elements[element["name"]] = {"text": caption}
                elif element["name"] == "logo":
                    payload_elements[element["name"]] = {
                        "url": "https://onlinepngtools.com/images/examples-onlinepngtools/google-logo-transparent.png"
                    }

            payload = {
                "template": template_name,
                "sizes": SOCIAL_MEDIA_PLATFORMS[platform]["sizes"],
                "elements": payload_elements,
            }
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
    selected_url: str,
    caption: str,
    platform: str,
    post_type: str,
) -> Dict[str, Any]:
    """Helper function to create an image using Switchboard Canvas"""
    canvas = SwitchboardCanvas()
    client_id = "351915950259"  # TODO: Delete this line
    payload = canvas.get_payload(client_id, selected_url, caption, platform, post_type)
    response = canvas.generate_image(payload)
    return response
