from heyoo.whatsapp import WhatsApp
from app.config import settings

def demonstrate_whatsapp_service():
    whatsapp = WhatsApp(
        token=settings.WHATSAPP_TOKEN,
        phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID
    )
    
    recipient = "+923408957390"
    
    response = whatsapp.send_message(
        to=recipient,
        message="Hello! Welcome to our service 👋",
        preview_url=True
    )
    print("Text message response:", response)

    image_response = whatsapp.send_image(
        to=recipient,
        image="https://example.com/welcome-image.jpg",
        caption="Welcome to our platform! 🌟"
    )
    print("Image message response:", image_response)

    
    button_data = {
        "body": "Would you like to proceed?",
        "buttons": [
            {
                "type": "reply",
                "reply": {
                    "id": "yes_button",
                    "title": "Yes"
                }
            },
            {
                "type": "reply",
                "reply": {
                    "id": "no_button",
                    "title": "No"
                }
            }
        ]
    }
    button_response = whatsapp.send_button(
        to=recipient,
        button_data=button_data
    )
    print("Button message response:", button_response)

if __name__ == "__main__":
    demonstrate_whatsapp_service()