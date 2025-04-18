import requests
from app.config import settings


def generate_template_name(platform: str, client_phone: str, post_type: str) -> str:
    """
    Generates a template name using the convention:
    SocialMediaPlatform_ClientPhoneNumber_PostType

    Args:
        platform (str): Social media platform (e.g., 'instagram').
        client_phone (str): Client phone number (digits only).
        post_type (str): Post type (should be predefined).

    Returns:
        str: The generated template name.
    """
    # NOTE: All post types should be defined in advance.
    return f"{platform.lower()}_{client_phone}_{post_type.lower()}"


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
    # Example usage for Instagram event post for client +351 915 950 259
    platform = "instagram"
    client_phone = "351915950259"
    post_type = "events"
    template = generate_template_name(platform, client_phone, post_type)
    sizes = [
        {"width": 1080, "height": 1080},  # Instagram size
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
