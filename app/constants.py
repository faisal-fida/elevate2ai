# WhatsApp message templates
MESSAGES = {
    # Original messages
    "welcome": "👋 Welcome! Please share your promotional text and I'll help you create engaging content.",
    "start_prompt": "👋 Please start by saying 'Hi'!",
    "generating": "🎨 Generating engaging content for your promotion...",
    "approval_prompt": "Please reply with 'y' to use this content or 'n' to generate a new variation.",
    "regenerating": "🔄 Let me generate a new variation for you...",
    "invalid_choice": "Please reply with either 'y' or 'n'.",
    "finalized": "✅ Great! Your content has been finalized.",
    "error": "❌ An error occurred. Please try again.",
    "content_type_selection": "👋 Now, let's create a post for your promotion. What type of content would you like to post?",
    "platform_selection_for_content": "📱 Great! For {content_type} content, you can post to these platforms. Please select one or 'All' to post to all supported platforms:",
    "caption_prompt": "✍️ Please provide instructions for generating your social media post:",
    "editing_confirmation": "🎨 I will process your content and post it to the selected platforms. Should I proceed?",
    "schedule_prompt": "🗓️ When would you like to post this content?",
    "confirmation_summary": "📋 Here's a summary of your post:\n\nContent Type: {content_type}\nPlatforms: {platforms}\nSchedule: {schedule}\nCaption: {caption}",
    "post_success": "✅ Your content has been posted successfully to {platforms}!",
    "post_partial_success": "⚠️ Your content was posted to some platforms: {success_platforms}\nFailed platforms: {failed_platforms}",
    "post_failure": "❌ Failed to post your content. Please try again.",
    "session_timeout": "⏰ Your session has timed out. Please start again by saying 'Hi'.",
    "menu_prompt": "Type 'Menu' to restart or 'Help' for assistance.",
    "image_inclusion_prompt": "🖼️ Would you like to include images in your post?",
}

# Social media platform image sizes and content types
SOCIAL_MEDIA_PLATFORMS = {
    "instagram": {
        "sizes": [{"width": 1080, "height": 1080}],
        "content_types": [
            "events",
            "destination",
            "promo",
            "tips",
            "seasonal",
            "reels",
        ],
    },
    "linkedin": {
        "sizes": [{"width": 1200, "height": 627}],
        "content_types": ["events", "tips", "seasonal"],
    },
    "tiktok": {
        "sizes": [{"width": 1080, "height": 1920}],
        "content_types": ["generic", "promo"],
    },
}


# Helper function to get platforms that support a specific content type
def get_platforms_for_content_type(content_type: str) -> list:
    """Return a list of platforms that support the given content type"""
    supported_platforms = []
    for platform, details in SOCIAL_MEDIA_PLATFORMS.items():
        if content_type in details["content_types"]:
            supported_platforms.append(platform)
    return supported_platforms


# Example OpenAI prompts (expand as needed)
OPENAI_PROMPTS = {
    "caption_system": "You are a marketing expert. Create engaging social media captions.",
    "caption_user": "Create an engaging caption for: {promo_text}",
    "search_system": "You are a marketing expert. Create a search query for finding relevant images. Just return the search query for platform like Unsplash nothing else.",
    "search_user": "Create a search query for: {caption}",
}


DEFAULT_TEMPLATE_CLIENT_ID = "923408957390"

# Legacy template data - kept for backward compatibility
# The new centralized configuration is in app/services/content/template_config.py
TEMPLATE_DATA = {
    # TikTok Templates
    f"tiktok_{DEFAULT_TEMPLATE_CLIENT_ID}_promo": {
        "type": "promo",
        "required_keys": [
            "destination_name",
            "video_background",
            "caption_text",
            "price_text",
        ],
    },
    f"tiktok_{DEFAULT_TEMPLATE_CLIENT_ID}_generic": {
        "type": "generic",
        "required_keys": ["caption_text", "video_background"],
    },
    # Instagram Templates
    f"instagram_{DEFAULT_TEMPLATE_CLIENT_ID}_reels": {
        "type": "reels",
        "required_keys": ["caption_text", "video_background"],
    },
    f"instagram_{DEFAULT_TEMPLATE_CLIENT_ID}_tips": {
        "type": "tips",
        "required_keys": ["main_image", "caption_text"],
    },
    f"instagram_{DEFAULT_TEMPLATE_CLIENT_ID}_promo": {
        "type": "promo",
        "required_keys": [
            "destination_name",
            "main_image",
            "caption_text",
            "price_text",
        ],
    },
    f"instagram_{DEFAULT_TEMPLATE_CLIENT_ID}_destination": {
        "type": "destination",
        "required_keys": ["destination_name", "main_image"],
    },
    f"instagram_{DEFAULT_TEMPLATE_CLIENT_ID}_events": {
        "type": "events",
        "required_keys": ["event_name", "main_image"],
    },
    f"instagram_{DEFAULT_TEMPLATE_CLIENT_ID}_seasonal": {
        "type": "seasonal",
        "required_keys": ["caption_text", "main_image"],
    },
    # LinkedIn Templates
    f"linkedin_{DEFAULT_TEMPLATE_CLIENT_ID}_tips": {
        "type": "tips",
        "required_keys": ["main_image", "caption_text"],
    },
    f"linkedin_{DEFAULT_TEMPLATE_CLIENT_ID}_seasonal": {
        "type": "seasonal",
        "required_keys": ["caption_text", "main_image"],
    },
    f"linkedin_{DEFAULT_TEMPLATE_CLIENT_ID}_events": {
        "type": "events",
        "required_keys": ["event_name", "main_image"],
    },
}
