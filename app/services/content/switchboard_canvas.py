import pandas as pd
import requests
from typing import Dict, List, Any
from dataclasses import dataclass
import logging
from app.config import settings
from app.constants import SOCIAL_MEDIA_PLATFORMS

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class TemplateElement:
    element_key: str
    element_type: str
    attributes: List[str]
    notes: str


class SwitchboardCanvas:
    def __init__(
        self,
        template_csv: str = "template.csv",
        api_key: str = None,
        base_url: str = "https://api.canvas.switchboard.ai",
    ):
        self.api_key = api_key or settings.SWITCHBOARD_API_KEY
        self.base_url = base_url.rstrip("/")
        self.templates: Dict[str, Dict[str, TemplateElement]] = {}
        self._load_templates(template_csv)
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _load_templates(self, file_path: str):
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            template_name = row["template_name"].strip()
            element = TemplateElement(
                element_key=row["element_key"].strip(),
                element_type=row["element_type"].strip(),
                attributes=[a.strip() for a in str(row["attributes"]).split(",") if a.strip()],
                notes=str(row.get("notes", "")).strip(),
            )
            if template_name not in self.templates:
                self.templates[template_name] = {}
            self.templates[template_name][element.element_key] = element

    def get_template_elements(self, template: str) -> List[Dict[str, Any]]:
        """Fetches the elements defined in a given template."""
        url = f"{self.base_url}/template/{template}/elements"
        try:
            print(url)
            exit(0)
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get("fields", [])
        except Exception as e:
            logger.error("Error fetching template elements: %s", e)
            raise e

    def generate_image(
        self,
        client_id: str,
        selected_url: str,
        caption: str,
        platform: str,
        post_type: str,
    ) -> Dict[str, Any]:
        template_name = f"{platform.lower()}_{client_id}_{post_type.lower()}"

        self.get_template_elements(template_name)

        elements = self.templates.get(template_name)
        if not elements:
            raise ValueError(f"Template not found: {template_name}")

        # Build payload for elements
        payload_elements = {}
        for key, element in elements.items():
            if element.element_type == "text":
                payload_elements[key] = {"text": caption}
            elif element.element_type in ("image", "video"):
                payload_elements[key] = {"url": selected_url}

        payload = {
            "template": template_name,
            "sizes": SOCIAL_MEDIA_PLATFORMS[platform]["sizes"],
            "elements": payload_elements,
        }

        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            logger.debug("Switchboard API response: %s", response.text)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Error generating image: %s", e)
            raise


if __name__ == "__main__":
    canvas = SwitchboardCanvas("template.csv")
    response = canvas.generate_image(
        client_id="351915950259",
        selected_url="https://images.unsplash.com/photo-1454496522488-7a8e488e8606",
        caption="This is a test caption.",
        platform="instagram",
        post_type="events",
    )
    print(response)
