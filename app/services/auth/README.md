# Authentication System

This authentication system uses WhatsApp numbers as primary identifiers while allowing Google OAuth linking for web dashboard access.

## Components

### Models

- **User**: Represents a user with WhatsApp number as primary identifier
- **OAuthConnection**: Represents a connection to an OAuth provider (e.g., Google)
- **Session**: Represents a user session

### Services

- **WhatsAppAuthService**: Handles WhatsApp-based authentication
- **GoogleOAuthService**: Handles Google OAuth integration
- **SessionService**: Manages user sessions
- **Security**: Provides JWT token handling

### API Routes

- **/api/auth/whatsapp**: WhatsApp authentication routes
- **/api/auth/google**: Google OAuth routes
- **/api/auth/session**: Session management routes

## Authentication Flow

### WhatsApp Authentication

1. User sends a message via WhatsApp
2. System authenticates user using WhatsApp number
3. User is created if not exists
4. Session is created for the user

### Google OAuth Linking

1. User initiates Google OAuth flow from web dashboard
2. User is redirected to Google for authentication
3. Google redirects back with authorization code
4. System exchanges code for tokens
5. Google account is linked to WhatsApp user
6. User is granted dashboard access

### Session Management

1. User logs in and receives access and refresh tokens
2. Access token is used for API requests
3. Refresh token is used to get new access tokens
4. Sessions can be revoked by the user

## Security

- JWT tokens are used for authentication
- Tokens have expiration times
- Sessions can be revoked
- CSRF protection for OAuth flow
