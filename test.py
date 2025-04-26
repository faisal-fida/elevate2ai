from app.services.content.canvas.switchboard import create_image


def test_create_image():
    response = create_image(
        client_id="351915950259",
        selected_url="https://www.elevateai.com/wp-content/uploads/2024/07/Rise-to-the-CX-Summit.jpg",
        caption="Test Caption",
        platform="instagram",
        post_type="events",
    )
    return response


print(test_create_image())
