import requests
from app.config import settings


def create_switchboard_image(api_key: str, template: str, sizes: list, elements: dict) -> dict:
    """
    Calls the Switchboard Canvas API to generate images.

    Args:
        api_key (str): Your Switchboard Canvas API key.
        template (str): The template API name.
        sizes (list): List of dicts with width, height, and optional elements.
        elements (dict): Overwrites for template elements.

    Returns:
        dict: The API response.
    """
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    payload = {"template": template, "sizes": sizes, "elements": elements}

    response = requests.post("https://api.canvas.switchboard.ai/", headers=headers, json=payload)
    try:
        response.raise_for_status()
    except requests.HTTPError:
        try:
            print("Response JSON:", response.json())
        except Exception:
            pass
        raise
    return response.json()


if __name__ == "__main__":
    api_key = settings.SWITCHBOARD_API_KEY
    template = "golden-gate"
    sizes = [
        {"width": 1920, "height": 1080},
    ]
    elements = {
        "backdrop": {"url": ""},
        "quote": {"text": ""},
        "person": {"text": ""},
        "quote-symbol": {"url": ""},
    }

    try:
        response = create_switchboard_image(api_key, template, sizes, elements)
        print("Image created successfully:", response)
    except requests.RequestException as e:
        print("Error creating image:", e)
    except Exception as e:
        print("An unexpected error occurred:", e)
