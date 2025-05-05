from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
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

            access_token = create_access_token(access_token_data)
            refresh_token = create_refresh_token(refresh_token_data)

            # Create session
            session = Session(
                id=str(uuid.uuid4()),
                whatsapp_number=whatsapp_number,
                token=access_token,
                refresh_token=refresh_token,
                user_agent=user_agent,
                ip_address=ip_address,
                device_info=str(device_info) if device_info else None,
                is_active=True,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=7),
                last_activity=datetime.utcnow(),
            )

            # Add session to database
            db.add(session)
            await db.commit()
            await db.refresh(session)

            # Update user's last login
            await db.execute(
                update(User)
                .where(User.whatsapp_number == whatsapp_number)
                .values(last_login=datetime.utcnow())
            )
            await db.commit()

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
    async def validate_session(db: AsyncSession, token: str) -> Optional[Session]:
        """
        Validate a session token
        """
        try:
            result = await db.execute(
                select(Session).where(
                    Session.token == token,
                    Session.is_active.is_(True),
                    Session.expires_at > datetime.utcnow(),
                )
            )
            session = result.scalars().first()

            if not session:
                return None

            # Update last activity
            session.last_activity = datetime.utcnow()
            await db.commit()

            return session

        except Exception as e:
            logger.error(f"Error validating session: {e}")
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
    async def revoke_session(db: AsyncSession, session_id: str) -> bool:
        """
        Revoke a session
        """
        try:
            result = await db.execute(
                update(Session).where(Session.id == session_id).values(is_active=False)
            )
            await db.commit()

            return result.rowcount > 0

        except Exception as e:
            logger.error(f"Error revoking session: {e}")
            await db.rollback()
            return False

    @staticmethod
    async def revoke_all_sessions(
        db: AsyncSession, whatsapp_number: str, except_session_id: Optional[str] = None
    ) -> bool:
        """
        Revoke all sessions for a user except the current one
        """
        try:
            query = update(Session).where(
                Session.whatsapp_number == whatsapp_number, Session.is_active.is_(True)
            )

            if except_session_id:
                query = query.where(Session.id != except_session_id)

            query = query.values(is_active=False)

            result = await db.execute(query)
            await db.commit()

            return result.rowcount > 0

        except Exception as e:
            logger.error(f"Error revoking all sessions: {e}")
            await db.rollback()
            return False

    @staticmethod
    async def cleanup_expired_sessions(db: AsyncSession) -> int:
        """
        Clean up expired sessions
        """
        try:
            result = await db.execute(
                delete(Session).where(Session.expires_at < datetime.utcnow())
            )
            await db.commit()

            return result.rowcount

        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            await db.rollback()
            return 0
