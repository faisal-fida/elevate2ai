# Elevate2AI

## Project Overview

Elevate2AI is a WhatsApp-based content generation and social media scheduling service built with FastAPI. Users interact via WhatsApp to generate engaging promotional captions, optionally include images, select platforms, schedule posts, and then automatically post to supported social media platforms.

## Features

- Interactive WhatsApp conversation for content creation  
- AI-generated captions with approval and regeneration options  
- Optional image inclusion via Pexels, Unsplash, Pixabay, and Switchboard Canvas API  
- Multi-platform support: Instagram, LinkedIn, TikTok (or All)  
- Content scheduling and automated posting  
- Secure authentication and admin user management  
- Session handling with refresh and revoke tokens  

## Technology Stack

- Python 3.12+  
- FastAPI + Uvicorn  
- SQLAlchemy (async) + SQLite  
- Pydantic & Pydantic-Settings  
- HTTPX for external API calls  
- OpenAI API for caption and search query generation  
- Switchboard Canvas API for post image creation  
- WhatsApp Business API for messaging  

## Prerequisites

- Python 3.12 or higher  
- WhatsApp Business API credentials  
- API keys for:  
  - Pexels  
  - Unsplash  
  - Pixabay  
  - Switchboard Canvas  
  - OpenAI  

## Installation

```bash
git clone https://github.com/your-org/elevate2ai.git
cd elevate2ai
python -m venv venv
source venv/bin/activate
pip install -r [`requirements.txt`](requirements.txt:1)
```

## Environment Variables

Create a [`.env`](.env:1) file in the project root with the following variables:

```
PROJECT_NAME=Elevate2AI
PROJECT_DESCRIPTION=Your project description
LOG_LEVEL=INFO
ENVIRONMENT=dev

DATABASE_PATH=./app.db
SQL_ECHO=False

JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

PEXELS_API_KEY=your-pexels-key
UNSPLASH_API_KEY=your-unsplash-key
PIXABAY_API_KEY=your-pixabay-key
SWITCHBOARD_API_KEY=your-switchboard-key

OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT=600.0
OPENAI_MAX_RETRIES=2

WHATSAPP_TOKEN=your-whatsapp-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_VERIFY_TOKEN=your-verify-token

ADMIN_WHATSAPP_NUMBER=admin-whatsapp-number
ADMIN_PASSWORD=admin-password

BACKEND_CORS_ORIGINS=http://localhost:3000
SECURE_COOKIES=False
TRUSTED_HOSTS=*
```

## Running the Application

Start the FastAPI server:

```bash
python [`run.py`](run.py:1)
```

The API will be available at `http://127.0.0.1:8000`.

## WhatsApp Webhook Setup

1. Expose your local server (e.g., using ngrok):  
   ```bash
   ngrok http 8000
   ```
2. Set the webhook URL in your WhatsApp Business dashboard to:  
   `https://<your-ngrok-url>/webhook`
3. Use the `WHATSAPP_VERIFY_TOKEN` for verification.

## Workflow Overview

Users interact with the bot through a multi-step state machine:

1. INIT: User sends "Hi" or "Hello".  
2. CONTENT_TYPE_SELECTION: Bot asks for content type.  
3. PLATFORM_SELECTION_FOR_CONTENT: Bot presents platform options.  
4. CAPTION_INPUT: Bot asks for promotional text.  
5. CAPTION_GENERATION: Bot generates caption and asks for approval.  
   - If user replies `n`, regenerates variation.  
   - If user replies `y`, proceeds.  
6. IMAGE_INCLUSION_DECISION: Bot asks if user wants to include images.  
   - `yes`: generates or searches images and presents options.  
   - `no`: skips to scheduling.  
7. SCHEDULE_SELECTION: Bot prompts for post date/time.  
   - Validates input or re-prompts on invalid.  
8. CONFIRMATION: Bot shows a summary:  
   ```
   Content Type: {content_type}
   Platforms: {platforms}
   Schedule: {schedule}
   Caption: {caption}
   ```  
   - User confirms with `y`.  
   - Or cancels/restarts on `n`.  
9. POST_EXECUTION: Bot posts content via ExecutionHandler:  
   - Immediate or scheduled posting to selected platforms.  
   - Uses SwitchboardCanvas for image rendering.  
   - Provides success/failure summary.  

## API Endpoints

### Authentication

- `POST /api/auth/register`: Register a new user.  
- `POST /api/auth/login`: Login and obtain tokens.  
- `POST /api/auth/session/refresh`: Refresh access token.  
- `POST /api/auth/session/revoke`: Revoke current session.  

### Webhook

- `GET /webhook`: Webhook verification.  
- `POST /webhook`: Process incoming WhatsApp messages.  

## Logs

Application logs are written to the `logs/` directory.

## Contributing

Contributions are welcome! Please open an issue or pull request.

## License

MIT License.