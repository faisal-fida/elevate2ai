# Authentication Examples

This directory contains examples of how to use the authentication system in the API.

## Getting Started

The authentication system uses WhatsApp numbers as primary identifiers while allowing Google OAuth linking for web dashboard access.

### Authentication Flow

1. **WhatsApp Authentication**:
   - User authenticates using their WhatsApp number
   - A session is created with access and refresh tokens
   - These tokens are used for subsequent API requests

2. **Google OAuth Linking** (optional, for dashboard access):
   - User initiates Google OAuth flow
   - User is redirected to Google for authentication
   - Google account is linked to WhatsApp user
   - User is granted dashboard access

## Example Files

- `auth_examples.py`: Contains examples of how to use the authentication endpoints

## Usage

To run the examples:

```bash
python examples/auth_examples.py
```

## Authentication Endpoints

### WhatsApp Authentication

- `POST /api/auth/whatsapp/authenticate`: Authenticate with WhatsApp number
- `POST /api/auth/whatsapp/verify/{whatsapp_number}`: Verify a WhatsApp number
- `GET /api/auth/whatsapp/me`: Get current user profile
- `PUT /api/auth/whatsapp/profile`: Update user profile

### Google OAuth

- `GET /api/auth/google/authorize?whatsapp_number={whatsapp_number}`: Start Google OAuth flow
- `GET /api/auth/google/callback`: Handle Google OAuth callback (used internally)

### Session Management

- `POST /api/auth/session/token`: Get access token (OAuth2 compatible)
- `POST /api/auth/session/refresh`: Refresh access token
- `POST /api/auth/session/revoke`: Revoke session(s)

## Authentication Headers

For protected endpoints, include the access token in the Authorization header:

```
Authorization: Bearer {access_token}
```
