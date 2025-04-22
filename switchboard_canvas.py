import logging
from typing import List, Dict, Any

import requests
from app.config import settings
from app.constants import SOCIAL_MEDIA_PLATFORMS

BASE_URL = "https://api.canvas.switchboard.ai"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SwitchboardCanvasClient:
    def __init__(self, api_key: str, base_url: str = BASE_URL) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def get_template_elements(self, template: str) -> List[Dict[str, Any]]:
        """Fetches the elements defined in a given template."""
        url = f"{self.base_url}/template/{template}/elements"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get("fields", [])
        except Exception as e:
            logger.error("Error fetching template elements: %s", e)
            raise e

    def generate_image(
        self, template: str, sizes: List[Dict[str, Any]], elements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calls the Switchboard Canvas API to generate images"""
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "template": template,
                    "sizes": sizes,
                    "elements": elements,
                },
            )
            logger.debug("Request Response: %s", response.text)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Error generating image: %s", e)
            raise e


def create_image(
    client_id: str, selected_url: str, caption: str, platform: str, post_type: str
) -> Dict[str, Any]:
    canvas_client = SwitchboardCanvasClient(api_key=settings.SWITCHBOARD_API_KEY)
    template = f"{platform.lower()}_{client_id}_{post_type.lower()}"
    sizes = SOCIAL_MEDIA_PLATFORMS[platform]["sizes"]

    # Fetch template elements
    fields = canvas_client.get_template_elements(template)
    elements = {}
    for field in fields:
        if field["type"] == "text":
            elements[field["name"]] = {"text": caption}
        elif field["type"] == "image":
            elements[field["name"]] = {"url": selected_url}
        elif field["type"] == "rectangle":
            elements[field["name"]] = {"fillColor": "#FF0000"}

    response = canvas_client.generate_image(template=template, sizes=sizes, elements=elements)
    return response


if __name__ == "__main__":
    # Example usage
    response = create_image(
        client_id="351915950259",
        selected_url="https://images.unsplash.com/photo-1454496522488-7a8e488e8606",
        caption="This is a test caption.",
        platform="instagram",
        post_type="events",
    )
    print(response)
