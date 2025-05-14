import httpx
from app.config import settings


def retrieve_text(media_id):
    """
    Downloads a media file from WhatsApp using the Media ID.

    Example webhook response format:
    {
        'from': '923408957390',
        'id': 'wamid.HBgMOTIzNDA4OTU3MzkwFQIAEhgWM0VCMEYyOTNBNTU0NUMwQjFDQzU5MgA=',
        'timestamp': '1747191936',
        'type': 'image',
        'image': {
            'mime_type': 'image/jpeg',
            'sha256': '6v8WKRouzX4frSkccvOFU+bTojosgbiCMsaVa/F03Yk=',
            'id': '681999801233256'
        }
    }
    """
    # For testing purposes - replace with actual media_id in production
    media_id = media_id or "714034044338587"

    # Step 1: Get media URL from WhatsApp Graph API
    response = httpx.get(
        f"https://graph.facebook.com/v17.0/{media_id}/",
        headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
    )
    data = response.json()

    # Example response data:
    # {
    #   'url': 'https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=714034044338587&ext=1747192045&hash=ATv7qOQfwpxidoxbLTi7sVBMpkxSG74xbJAw1JTAW6QP3Q',
    #   'mime_type': 'image/png',
    #   'sha256': '435e47a077a9b3d6fb65d2aec1a70e129f9783b2ad103ce85b7476f6f356892a',
    #   'file_size': 257546,
    #   'id': '714034044338587',
    #   'messaging_product': 'whatsapp'
    # }

    # Step 2: Download the actual media file
    with open("image.png", "wb") as file:
        image_response = httpx.get(
            data.get("url"),
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
        )

        if image_response.status_code == 200:
            file.write(image_response.content)
            print("Image downloaded successfully.")
            return True
        else:
            print(
                f"Failed to download image. Status code: {image_response.status_code}"
            )
            return False
