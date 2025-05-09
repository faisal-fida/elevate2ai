from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from app.models.session import Session
from app.models.user import User
from app.services.auth.security import create_access_token, create_refresh_token
from app.services.common.logging import setup_logger
from app.config import settings
import uuid

logger = setup_logger(__name__)


class SessionService:
    """
    Service for managing user sessions
    """

    @staticmethod
    async def create_session(
        db: AsyncSession,
        whatsapp_number: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_info: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new session for a user
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

            # Create tokens
            access_token_data = {"sub": whatsapp_number}
            refresh_token_data = {"sub": whatsapp_number}
            access_token_jti = str(uuid.uuid4())
            access_token = create_access_token(access_token_data, jti=access_token_jti)
            refresh_token = create_refresh_token(refresh_token_data)

            # Create session
            session = Session(
                id=access_token_jti,
                whatsapp_number=whatsapp_number,
                token=access_token,
                refresh_token=refresh_token,
                user_agent=user_agent,
                ip_address=ip_address,
                device_info=device_info,
                is_active=True,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow()
                + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
                last_activity=datetime.utcnow(),
            )

            # Add session and update user's last login in one transaction
            db.add(session)
            await db.execute(
                update(User)
                .where(User.whatsapp_number == whatsapp_number)
                .values(last_login=datetime.utcnow())
            )
            await db.commit()
            await db.refresh(session)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "session_id": session.id,
            }

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            await db.rollback()
            return None

    @staticmethod
    async def refresh_session(
        db: AsyncSession, refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh a session using a refresh token
        """
        try:
            result = await db.execute(
                select(Session).where(
                    Session.refresh_token == refresh_token,
                    Session.is_active.is_(True),
                    Session.expires_at > datetime.utcnow(),
                )
            )
            session = result.scalars().first()

            if not session:
                logger.error("Invalid refresh token or expired session")
                return None

            # Create new access token
            access_token_data = {"sub": session.whatsapp_number}
            new_access_token = create_access_token(access_token_data)

            # Update session
            session.token = new_access_token
            session.last_activity = datetime.utcnow()
            await db.commit()

            return {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            }

        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            return None

    @staticmethod
    async def revoke_session_by_jti(
        db: AsyncSession, session_jti: str, whatsapp_number: str
    ) -> bool:
        """
        Revoke a specific session by its JTI (JWT ID) for a given user.
        Ensures that a user can only revoke their own sessions.
        """
        try:
            result = await db.execute(
                update(Session)
                .where(
                    Session.id == session_jti,
                    Session.whatsapp_number == whatsapp_number,
                    Session.is_active,
                )
                .values(is_active=False, expires_at=datetime.now(timezone.utc))
            )
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(
                f"Error revoking session by JTI {session_jti} for user {whatsapp_number}: {e}"
            )
            await db.rollback()
            return False
