# WhatsApp message templates
MESSAGES = {
    "welcome": "👋 Welcome! Please share your promotional text and I'll help you create engaging content.",
    "start_prompt": "👋 Please start by saying 'Hi'!",
    "generating": "🎨 Generating engaging content for your promotion...",
    "approval_prompt": "Please reply with 'y' to use this content or 'n' to generate a new variation.",
    "regenerating": "🔄 Let me generate a new variation for you...",
    "invalid_choice": "Please reply with either 'y' or 'n'.",
    "finalized": "✅ Great! Your content has been finalized.",
    "error": "❌ An error occurred. Please try again.",
}

# Social media platform image sizes
SOCIAL_MEDIA_PLATFORMS = {
    "instagram": {"sizes": [{"width": 1080, "height": 1080}]},
    "tiktok": {"sizes": [{"width": 1080, "height": 1920}]},
    "linkedin": {"sizes": [{"width": 1200, "height": 627}]},
}

# Example OpenAI prompts (expand as needed)
OPENAI_PROMPTS = {
    "caption_system": "You are a marketing expert. Create engaging social media captions.",
    "caption_user": "Create an engaging caption for: {promo_text}",
    "search_system": "You are a marketing expert. Create a search query for finding relevant images. Just return the search query for platform like Unsplash nothing else.",
    "search_user": "Create a search query for: {caption}",
}
