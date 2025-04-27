from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.services.auth.session import SessionService
from app.services.common.logging import setup_logger
import json

logger = setup_logger(__name__)


class WhatsAppAuthService:
    """
    Service for WhatsApp-based authentication
    """

    @staticmethod
    async def authenticate_whatsapp(
        db: AsyncSession,
        whatsapp_number: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_info: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user using WhatsApp number
        """
        try:
            # Check if user exists
            result = await db.execute(select(User).where(User.whatsapp_number == whatsapp_number))
            user = result.scalars().first()

            # If user doesn't exist, create a new one
            if not user:
                logger.info(f"Creating new user with WhatsApp number {whatsapp_number}")
                user = User(
                    whatsapp_number=whatsapp_number,
                    is_active=True,
                    is_verified=True,  # WhatsApp numbers are considered verified
                    has_dashboard_access=False,  # No dashboard access until Google OAuth
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)

            # Create a session for the user
            session_data = await SessionService.create_session(
                db=db,
                whatsapp_number=whatsapp_number,
                user_agent=user_agent,
                ip_address=ip_address,
                device_info=device_info,
            )

            if not session_data:
                logger.error(f"Failed to create session for WhatsApp number {whatsapp_number}")
                return None

            # Return user data and session
            return {
                "user": {
                    "whatsapp_number": user.whatsapp_number,
                    "name": user.name,
                    "email": user.email,
                    "has_dashboard_access": user.has_dashboard_access,
                },
                "session": session_data,
            }

        except Exception as e:
            logger.error(f"Error authenticating WhatsApp user: {e}")
            await db.rollback()
            return None

    @staticmethod
    async def verify_whatsapp_number(db: AsyncSession, whatsapp_number: str) -> bool:
        """
        Verify a WhatsApp number (mark as verified)
        """
        try:
            # Check if user exists
            result = await db.execute(select(User).where(User.whatsapp_number == whatsapp_number))
            user = result.scalars().first()

            if not user:
                logger.error(f"User with WhatsApp number {whatsapp_number} not found")
                return False

            # Mark as verified
            user.is_verified = True
            await db.commit()

            return True

        except Exception as e:
            logger.error(f"Error verifying WhatsApp number: {e}")
            await db.rollback()
            return False

    @staticmethod
    async def update_user_profile(
        db: AsyncSession,
        whatsapp_number: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        profile_picture: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[User]:
        """
        Update a user's profile information
        """
        try:
            # Check if user exists
            result = await db.execute(select(User).where(User.whatsapp_number == whatsapp_number))
            user = result.scalars().first()

            if not user:
                logger.error(f"User with WhatsApp number {whatsapp_number} not found")
                return None

            # Update fields if provided
            if name:
                user.name = name
            if email:
                user.email = email
            if profile_picture:
                user.profile_picture = profile_picture
            if metadata:
                # Merge with existing metadata if any
                existing_metadata = {}
                if user.metadata_json:
                    try:
                        existing_metadata = json.loads(user.metadata_json)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in metadata for user {whatsapp_number}")
                        existing_metadata = {}

                # Update with new metadata
                existing_metadata.update(metadata)
                user.metadata_json = json.dumps(existing_metadata)

            await db.commit()
            await db.refresh(user)

            return user

        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            await db.rollback()
            return None
