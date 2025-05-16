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

### Run the Application

```bash
python run.py
```

Server runs at `http://127.0.0.1:8000`

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