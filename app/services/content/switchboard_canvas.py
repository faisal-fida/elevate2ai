import requests
from typing import Dict, List, Any
import logging
from app.config import settings
from app.constants import SOCIAL_MEDIA_PLATFORMS

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SwitchboardCanvas:
    def __init__(self, base_url: str = "https://api.canvas.switchboard.ai"):
        self.api_key = settings.SWITCHBOARD_API_KEY
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

    def get_payload(
        self,
        client_id: str,
        selected_url: str,
        caption: str,
        platform: str,
        post_type: str,
    ) -> Dict[str, Any]:
        try:
            template_name = f"{platform.lower()}_{client_id}_{post_type.lower()}"
            elements = self.get_template_elements(template_name)
            logger.debug("Elements: %s", elements)

            for element in elements:
                if element["name"] == "caption":
                    element["value"] = caption
                elif element["name"] == "image":
                    element["value"] = selected_url

            payload = {
                "template": template_name,
                "sizes": SOCIAL_MEDIA_PLATFORMS[platform]["sizes"],
                "elements": elements,
            }
            return payload
        except Exception as e:
            logger.error("Error creating payload: %s", e)
            raise

    def generate_image(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            logger.debug("Switchboard API response: %s", response.text)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Error generating image: %s", e)
            raise


def create_image(
    client_id: str,
    selected_url: str,
    caption: str,
    platform: str,
    post_type: str,
) -> Dict[str, Any]:
    canvas = SwitchboardCanvas()
    payload = canvas.get_payload(client_id, selected_url, caption, platform, post_type)
    response = canvas.generate_image(payload)
    return response


# if __name__ == "__main__":
#     canvas = SwitchboardCanvas("template.csv")
#     response = canvas.generate_image(
#         client_id="351915950259",
#         selected_url="https://images.unsplash.com/photo-1454496522488-7a8e488e8606",
#         caption="This is a test caption.",
#         platform="instagram",
#         post_type="events",
#     )
#     print(response)
