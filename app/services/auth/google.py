from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.models.oauth import OAuthConnection
from app.services.common.logging import setup_logger
from app.config import settings
import httpx
import uuid
from datetime import datetime, timedelta

logger = setup_logger(__name__)


class GoogleOAuthService:
    """
    Service for Google OAuth integration
    """

    @staticmethod
    def get_authorization_url(state: str) -> str:
        """
        Get the Google OAuth authorization URL
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_REDIRECT_URI:
            logger.error("Google OAuth is not configured")
            return ""

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "state": state,
            "prompt": "consent",
        }

        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])

        return f"https://accounts.google.com/o/oauth2/auth?{query_string}"

    @staticmethod
    async def exchange_code_for_tokens(code: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access and refresh tokens
        """
        if (
            not settings.GOOGLE_CLIENT_ID
            or not settings.GOOGLE_CLIENT_SECRET
            or not settings.GOOGLE_REDIRECT_URI
        ):
            logger.error("Google OAuth is not configured")
            return None

        try:
            # Prepare token request
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            }

            # Make request
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=data)
                response.raise_for_status()

                return response.json()

        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            return None

    @staticmethod
    async def get_user_info(access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from Google using access token
        """
        try:
            # Prepare user info request
            userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}

            # Make request
            async with httpx.AsyncClient() as client:
                response = await client.get(userinfo_url, headers=headers)
                response.raise_for_status()

                return response.json()

        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None

    @staticmethod
    async def link_google_account(
        db: AsyncSession,
        whatsapp_number: str,
        google_user_id: str,
        google_email: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expiry: Optional[datetime] = None,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[User, OAuthConnection]]:
        """
        Link a Google account to a WhatsApp user
        """
        try:
            # Check if user exists
            result = await db.execute(
                select(User).where(User.whatsapp_number == whatsapp_number)
            )
            user = result.scalars().first()

            if not user:
                logger.error(f"User with WhatsApp number {whatsapp_number} not found")
                return None

            # Check if this Google account is already linked to another user
            result = await db.execute(
                select(OAuthConnection).where(
                    OAuthConnection.provider == "google",
                    OAuthConnection.provider_user_id == google_user_id,
                )
            )
            existing_connection = result.scalars().first()

            if (
                existing_connection
                and existing_connection.whatsapp_number != whatsapp_number
            ):
                logger.error(
                    f"Google account already linked to another WhatsApp number {existing_connection.whatsapp_number}"
                )
                return None

            # Create or update OAuth connection
            if existing_connection:
                # Update existing connection
                existing_connection.access_token = access_token
                existing_connection.refresh_token = (
                    refresh_token
                    if refresh_token
                    else existing_connection.refresh_token
                )
                existing_connection.token_expiry = token_expiry
                existing_connection.last_used = datetime.utcnow()
                oauth_connection = existing_connection
            else:
                # Create new connection
                oauth_connection = OAuthConnection(
                    id=str(uuid.uuid4()),
                    whatsapp_number=whatsapp_number,
                    provider="google",
                    provider_user_id=google_user_id,
                    provider_email=google_email,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expiry=token_expiry,
                    last_used=datetime.utcnow(),
                )
                db.add(oauth_connection)

            # Update user profile with Google info if available
            if user_info:
                user.name = user_info.get("name", user.name)
                user.email = user_info.get("email", user.email)
                user.profile_picture = user_info.get("picture", user.profile_picture)

                # Enable dashboard access
                user.has_dashboard_access = True

            await db.commit()
            await db.refresh(oauth_connection)
            await db.refresh(user)

            return (user, oauth_connection)

        except Exception as e:
            logger.error(f"Error linking Google account: {e}")
            await db.rollback()
            return None

    @staticmethod
    async def refresh_google_token(
        db: AsyncSession, oauth_connection_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh a Google OAuth token
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            logger.error("Google OAuth is not configured")
            return None

        try:
            # Get OAuth connection
            result = await db.execute(
                select(OAuthConnection).where(OAuthConnection.id == oauth_connection_id)
            )
            oauth_connection = result.scalars().first()

            if (
                not oauth_connection
                or oauth_connection.provider != "google"
                or not oauth_connection.refresh_token
            ):
                logger.error(
                    f"Invalid OAuth connection or missing refresh token for {oauth_connection_id}"
                )
                return None

            # Prepare token refresh request
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": oauth_connection.refresh_token,
                "grant_type": "refresh_token",
            }

            # Make request
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=data)
                response.raise_for_status()

                token_data = response.json()

                # Update OAuth connection
                oauth_connection.access_token = token_data.get("access_token")
                oauth_connection.token_expiry = datetime.utcnow() + timedelta(
                    seconds=token_data.get("expires_in", 3600)
                )
                oauth_connection.last_used = datetime.utcnow()

                await db.commit()

                return token_data

        except Exception as e:
            logger.error(f"Error refreshing Google token: {e}")
            await db.rollback()
            return None

    @staticmethod
    async def unlink_google_account(db: AsyncSession, whatsapp_number: str) -> bool:
        """
        Unlink a Google account from a WhatsApp user
        """
        try:
            # Get OAuth connection
            result = await db.execute(
                select(OAuthConnection).where(
                    OAuthConnection.whatsapp_number == whatsapp_number,
                    OAuthConnection.provider == "google",
                )
            )
            oauth_connection = result.scalars().first()

            if not oauth_connection:
                logger.error(
                    f"No Google account linked to WhatsApp number {whatsapp_number}"
                )
                return False

            # Delete OAuth connection
            await db.delete(oauth_connection)

            # Update user
            result = await db.execute(
                select(User).where(User.whatsapp_number == whatsapp_number)
            )
            user = result.scalars().first()

            if user:
                # Disable dashboard access
                user.has_dashboard_access = False

            await db.commit()

            return True

        except Exception as e:
            logger.error(f"Error unlinking Google account: {e}")
            await db.rollback()
            return False
