import httpx
import urllib.parse

whatsapp_url = "https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=1446721650015555&ext=1747215200&hash=ATvg1EcZ1zEkQl1Kk8NibGoiVKTpCltcKolamwFr94Slyg"
encoded_url = urllib.parse.quote(whatsapp_url, safe="")

api_url = f"https://didactic-space-guide-q6x5rqx6xqjh9rxr-8000.app.github.dev/api/media-proxy?url={encoded_url}"

with httpx.Client() as client:
    response = client.get(api_url)
    if response.status_code == 200:
        print("Media retrieved successfully")
        with open("media.jpg", "wb") as f:
            f.write(response.content)
    else:
        print(f"Failed to retrieve media: {response.status_code} - {response.text}")
