# Elevate2AI

A WhatsApp-based content generation and social media scheduling service built with FastAPI.

## Features

- WhatsApp interaction for creating and scheduling social media content
- AI-generated captions using OpenAI
- Media handling (upload or search for stock images/videos)
- Multi-platform publishing (Instagram, LinkedIn, TikTok)
- Content scheduling and automated posting

## Quick Start

### Prerequisites

- Python 3.12+
- WhatsApp Business API credentials
- API keys for OpenAI and media services (Pexels, Unsplash, Pixabay)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/elevate2ai.git
cd elevate2ai

# Set up environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies with uv
uv sync
```

### Configuration

Create a `.env` file in the project root:

```
# Core settings
PROJECT_NAME=Elevate2AI
PROJECT_DESCRIPTION=WhatsApp content generation service
ENVIRONMENT=dev
LOG_LEVEL=INFO

# Database
DATABASE_PATH=./app.db
SQL_ECHO=False

# Security
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
BACKEND_CORS_ORIGINS=http://localhost:3000
SECURE_COOKIES=False
TRUSTED_HOSTS=*

# External APIs
PEXELS_API_KEY=your-pexels-key
UNSPLASH_API_KEY=your-unsplash-key
PIXABAY_API_KEY=your-pixabay-key
SWITCHBOARD_API_KEY=your-switchboard-key

# OpenAI
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT=600.0
OPENAI_MAX_RETRIES=2

# WhatsApp
WHATSAPP_TOKEN=your-whatsapp-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_VERIFY_TOKEN=your-verify-token

# Admin
ADMIN_WHATSAPP_NUMBER=admin-whatsapp-number
ADMIN_PASSWORD=admin-password
```

### Run the Application

```bash
python run.py
```

Server runs at `http://127.0.0.1:8000`

## Project Structure

```
.
├── app/                    # Main application package
│   ├── api/                # API endpoints
│   │   ├── auth/           # Authentication routes
│   │   └── webhook.py      # WhatsApp webhook handler
│   ├── models/             # Database models
│   │   ├── session.py      # User session model
│   │   └── user.py         # User model
│   ├── services/           # Business logic
│   │   ├── auth/           # Authentication services
│   │   ├── common/         # Shared utilities
│   │   ├── content/        # Content generation
│   │   ├── messaging/      # WhatsApp messaging
│   │   └── workflow/       # Conversation flow
│   ├── config.py           # Application settings
│   ├── db.py               # Database setup
│   ├── main.py             # FastAPI application
│   ├── middleware.py       # Custom middleware
│   └── schemas.py          # Pydantic models
├── media/                  # Media storage
├── pyproject.toml          # Project dependencies
├── README.md               # This file
├── run.py                  # Application entry point
└── uv.lock                 # Dependency lock file
```

## Core Workflows

Users interact with the bot through WhatsApp:

1. **Start conversation** - User sends a greeting
2. **Content selection** - Choose content type 
3. **Platform selection** - Select target platforms
4. **Content creation** - Input or generate captions
5. **Media selection** - Upload or search for media
6. **Scheduling** - Set post date/time
7. **Publication** - Confirm and post to platforms

## Development

### Package Management

This project uses `uv` for dependency management:

```bash
# Add packages
uv add package-name

# Remove packages
uv remove package-name

# Sync dependencies
uv sync
```

### Running Tests

```bash
uv run -m pytest
```

### WhatsApp Webhook Setup

1. Expose your local server (using ngrok or similar)
2. Set webhook URL in WhatsApp Business dashboard:
   `https://your-domain.com/webhook`
3. Use `WHATSAPP_VERIFY_TOKEN` for verification

## API Documentation

When the app is running:
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## License

MIT License