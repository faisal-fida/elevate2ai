# Services Directory Structure

This directory contains the core services of the application, organized in a modular way to improve maintainability and scalability.

## Directory Structure

```
services/
├── common/                  # Common utilities and types
│   ├── logging.py           # Centralized logging configuration
│   └── types.py             # Common type definitions
│
├── content/                 # Content generation services
│   ├── ai/                  # AI services
│   │   └── openai_service.py # OpenAI integration
│   ├── canvas/              # Canvas services
│   │   └── switchboard.py   # Switchboard Canvas integration
│   ├── media/               # Media services
│   │   ├── image_service.py # Image search service
│   │   └── providers/       # Media providers
│   │       ├── unsplash.py  # Unsplash provider
│   │       ├── pexels.py    # Pexels provider
│   │       └── pixabay.py   # Pixabay provider
│   └── generator.py         # Content generator
│
├── messaging/               # Messaging services
│   ├── client.py            # Messaging client (WhatsApp)
│   ├── handlers/            # Message handlers
│   │   ├── base.py          # Base handler
│   │   └── whatsapp.py      # WhatsApp handler
│   └── state_manager.py     # State management
│
└── workflow/                # Workflow services
    ├── base.py              # Base workflow
    ├── manager.py           # Workflow manager
    ├── social_media.py      # Social media workflow
    └── handlers/            # Workflow handlers
        ├── base.py          # Base handler
        ├── platform_selection.py # Platform selection handler
        ├── content_type.py  # Content type handler
        ├── caption.py       # Caption handler
        ├── scheduling.py    # Scheduling handler
        └── execution.py     # Execution handler
```

## Service Components

### Common

Contains shared utilities and type definitions used across the application.

### Content

Services for generating and managing content:
- AI integration for text generation
- Media services for image search
- Canvas services for image generation

### Messaging

Services for sending and receiving messages:
- Messaging clients (WhatsApp)
- Message handlers
- State management

### Workflow

Services for managing workflows:
- Workflow manager
- Social media workflow
- Workflow handlers for each step of the process

## Usage

The main entry point is the `WorkflowManager` class in `workflow/manager.py`, which is used by the webhook handler to process incoming messages.

Example:
```python
from app.services.workflow.manager import WorkflowManager

# Initialize the workflow manager
workflow_manager = WorkflowManager()

# Process a message
await workflow_manager.process_message(client_id, message)
```
