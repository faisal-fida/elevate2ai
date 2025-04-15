# WhatsApp Content Generation Service

## Setup Instructions

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
Create a `.env` file in the project root with:
```env
WHATSAPP_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token
```

3. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

4. Expose webhook for WhatsApp (using ngrok):
```bash
ngrok http 8000
```

5. Configure Webhook in Meta Developer Portal:
- Use the ngrok HTTPS URL as your webhook URL
- Append `/webhook` to the URL
- Use your `WHATSAPP_VERIFY_TOKEN` for verification

## Testing the Service

1. **Manual Testing via WhatsApp:**
- Send "Hi" to your WhatsApp business number
- Follow the prompts to test content generation
- Try approving and rejecting generated content

2. **Development Testing:**
Run the test script:
```bash
python wa.py
```

## Features
- Automated content generation workflow
- Message queueing and rate limiting
- State management for multiple clients
- Media handling capabilities
- Webhook integration for real-time updates

## API Endpoints
- `GET /webhook` - WhatsApp webhook verification
- `POST /webhook` - Incoming message handler