# Services Overview

This directory contains the core business logic and services for the Elevate2AI application.

## Directory Structure

```
services/
├── auth/               # Authentication and authorization
│   ├── security.py     # Password hashing, JWT generation
│   ├── session.py      # User session management
│   └── whatsapp.py     # Auth service for WhatsApp users
│
├── common/             # Shared utilities
│   ├── logging.py      # Centralized logging configuration
│   └── types.py        # Common type definitions
│
├── content/            # Content generation
│   ├── generator.py    # Main content generation orchestration
│   ├── image_service.py # Media search and retrieval
│   ├── openai_service.py # OpenAI integration
│   ├── switchboard.py  # Switchboard Canvas integration
│   └── template_utils.py # Template rendering utilities
│
├── messaging/          # WhatsApp messaging
│   ├── client.py       # WhatsApp API client
│   ├── media_utils.py  # Media handling utilities
│   └── state_manager.py # Conversation state management
│
└── workflow/           # Conversation workflow
    ├── manager.py      # Main workflow orchestration
    ├── base.py         # Base workflow handler
    └── handlers/       # State-specific message handlers
```

## Usage Examples

### Authentication

```python
from app.services.auth import (
    AuthService, 
    get_password_hash, 
    verify_password,
    create_access_token
)

# Create a hashed password
hashed_password = get_password_hash("secure_password")

# Verify a password
is_valid = verify_password("user_input", hashed_password)

# Create a JWT token
token = create_access_token({"sub": "user@example.com"})
```

### WhatsApp Messaging

```python
from app.services.messaging import WhatsApp

# Initialize the client
whatsapp = WhatsApp(token="your_token", phone_number_id="your_number_id")

# Send a simple text message
await whatsapp.send_message(
    message="Hello from Elevate2AI!",
    phone_number="1234567890"
)

# Send buttons
await whatsapp.send_interactive_buttons(
    header_text="Choose an option",
    body_text="Please select a platform:",
    buttons=[
        {"id": "instagram", "title": "Instagram"},
        {"id": "linkedin", "title": "LinkedIn"}
    ],
    phone_number="1234567890"
)
```

### Content Generation

```python
from app.services.content import ContentGenerator, OpenAIService

# Generate captions
content_generator = ContentGenerator()
caption = await content_generator.generate_caption(
    content_type="event",
    prompt="Tech conference in London"
)

# Direct OpenAI integration
openai_service = OpenAIService()
response = await openai_service.generate_completion(
    prompt="Generate a promotional caption for a new coffee shop"
)
```

### Workflow Management

```python
from app.services.workflow import WorkflowManager
from app.services.messaging import StateManager, WorkflowState

# Initialize components
state_manager = StateManager()
workflow_manager = WorkflowManager()

# Process an incoming message
await workflow_manager.process_message(
    client_id="1234567890",
    message="Hi"
)

# Manually manage state
state_manager.set_state(
    client_id="1234567890",
    state=WorkflowState.CONTENT_TYPE_SELECTION
)
```

## Extending Services

When adding new functionality:

1. Choose the appropriate service category (or create a new one if needed)
2. Follow the established patterns and naming conventions
3. Use dependency injection for service dependencies
4. Add imports to the package's `__init__.py` to simplify imports
5. Document your service with docstrings and update this README 