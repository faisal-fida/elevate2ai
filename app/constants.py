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
    # New messages for social media posting workflow
    "platform_selection": "👋 Now, let's create a post for your promotion. Please select the platforms where you want to post:",
    "platform_selection_done": "✅ You've selected: {platforms}. Select 'Done' when you're finished.",
    "content_type_selection": "📝 What type of content would you like to post?",
    "same_content_prompt": "🤔 Would you like to post the same content on all selected platforms?",
    "platform_specific_content": "📱 Let's select content type for {platform}:",
    "caption_prompt": "✍️ Please enter a caption for your post:",
    "schedule_prompt": "🗓️ When would you like to post this content?",
    "confirmation_summary": "📋 Here's a summary of your post:\n\nPlatforms: {platforms}\nContent Types: {content_types}\nSchedule: {schedule}\nCaption: {caption}\n\nIs this correct?",
    "post_success": "✅ Your content has been posted successfully to {platforms}!",
    "post_partial_success": "⚠️ Your content was posted to some platforms: {success_platforms}\nFailed platforms: {failed_platforms}",
    "post_failure": "❌ Failed to post your content. Please try again.",
    "session_timeout": "⏰ Your session has timed out. Please start again by saying 'Create Post'.",
    "menu_prompt": "Type 'Menu' to restart or 'Help' for assistance.",
}

# Social media platform image sizes and content types
SOCIAL_MEDIA_PLATFORMS = {
    "instagram": {
        "sizes": [{"width": 1080, "height": 1080}],
        "content_types": ["events", "destination", "promo", "tips", "seasonal", "reels"],
    },
    "linkedin": {
        "sizes": [{"width": 1200, "height": 627}],
        "content_types": ["events", "tips", "seasonal"],
    },
    "tiktok": {"sizes": [{"width": 1080, "height": 1920}], "content_types": ["generic", "promo"]},
}

# Example OpenAI prompts (expand as needed)
OPENAI_PROMPTS = {
    "caption_system": "You are a marketing expert. Create engaging social media captions.",
    "caption_user": "Create an engaging caption for: {promo_text}",
    "search_system": "You are a marketing expert. Create a search query for finding relevant images. Just return the search query for platform like Unsplash nothing else.",
    "search_user": "Create a search query for: {caption}",
}
