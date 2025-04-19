import logging
from typing import List, Dict, Any

import requests
from app.config import settings

BASE_URL = "https://api.canvas.switchboard.ai/"
SOCIAL_MEDIA_PLATFORMS = {
    "instagram": {"sizes": [{"width": 1080, "height": 1080}]},
    "tiktok": {"sizes": [{"width": 1080, "height": 1920}]},
    "linkedin": {"sizes": [{"width": 1200, "height": 627}]},
}

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

    def create_image(
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
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as http_err:
            logger.error("HTTP error occurred: %s", http_err)
            try:
                error_json = response.json()
                logger.debug("Response JSON: %s", error_json)
            except ValueError:
                pass
            raise
        except Exception as err:
            logger.exception(f"Unexpected error occurred while creating image: {err}")
            raise


def create_image(
    client_id: str, selected_url: str, caption: str, platform: str, post_type: str
) -> None:
    """Creates an image using the Switchboard Canvas API"""
    logger.info(
        f"Creating social media post. Client ID: {client_id}, Image URL: {selected_url}, Caption: {caption}, Platform: {platform}, Post Type: {post_type}"
    )
    canvas_client = SwitchboardCanvasClient(api_key=settings.SWITCHBOARD_API_KEY)

    template = f"{platform.lower()}_{client_id}_{post_type.lower()}"
    sizes = SOCIAL_MEDIA_PLATFORMS[platform]["sizes"]
    elements = {
        "backdrop": {"url": selected_url},
        "quote": {"text": caption},
        "person": {"text": ""},
        "quote-symbol": {"url": ""},
    }

    elements = {
        "backdrop": {"url": "https://via.placeholder.com/500/500"},
        "border": {"fillColor": "#FF0000"},
        "cta_details": {"text": "Fala connosco!"},
        "cta_title": {"text": "Reserva Fácil e Rápida."},
        "logo": {"url": "https://via.placeholder.com/500/500"},
    }

    try:
        response = canvas_client.create_image(template, sizes, elements)
        logger.info("Image created successfully: %s", response)
    except Exception as e:
        logger.error("Error creating image: %s", e)
        raise e
