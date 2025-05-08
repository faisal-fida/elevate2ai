from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from app.models.user import User
from app.services.auth.session import SessionService
from app.services.common.logging import setup_logger
from app.schemas import UserCreate, UserResponse, AdminUserUpdateAccess
from app.config import settings

logger = setup_logger(__name__)


class AuthService:
    """
    Service for user authentication and management.
    """

    @staticmethod
    async def get_user_by_whatsapp(
        db: AsyncSession, whatsapp_number: str
    ) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.whatsapp_number == whatsapp_number)
        )
        return result.scalars().first()

    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        """
        Create a new user.
        """
        existing_user = await AuthService.get_user_by_whatsapp(
            db, user_data.whatsapp_number
        )
        if existing_user:
            logger.warning(
                f"User with WhatsApp number {user_data.whatsapp_number} already exists."
            )
            raise ValueError("User already exists")

        is_admin_user = user_data.whatsapp_number == settings.ADMIN_WHATSAPP_NUMBER

        new_user = User(
            whatsapp_number=user_data.whatsapp_number,
            is_active=True,
            is_admin=is_admin_user,
            has_dashboard_access=is_admin_user,
        )
        new_user.set_password(user_data.password)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        logger.info(f"Created new user with WhatsApp number {new_user.whatsapp_number}")
        return new_user

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        whatsapp_number: str,
        password: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_info: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user with WhatsApp number and password.
        Creates a user if they don't exist.
        """
        try:
            user = await AuthService.get_user_by_whatsapp(db, whatsapp_number)

            if not user:
                logger.info(f"User {whatsapp_number} not found. Creating new user.")
                user_create_data = UserCreate(
                    whatsapp_number=whatsapp_number, password=password
                )
                user = await AuthService.create_user(db, user_create_data)
            elif not user.verify_password(password):
                logger.warning(f"Invalid password for user {whatsapp_number}")
                return None

            if not user.is_active:
                logger.warning(f"User {whatsapp_number} is inactive.")
                return None

            session_data = await SessionService.create_session(
                db=db,
                whatsapp_number=user.whatsapp_number,
                user_agent=user_agent,
                ip_address=ip_address,
                device_info=device_info,
            )

            if not session_data:
                logger.error(f"Failed to create session for user {whatsapp_number}")
                return None

            return {
                "user": UserResponse.from_orm(user).dict(),
                "session": session_data,
            }

        except Exception as e:
            logger.error(f"Error authenticating user {whatsapp_number}: {e}")
            await db.rollback()
            return None

    @staticmethod
    async def get_all_users(db: AsyncSession) -> List[UserResponse]:
        """
        Retrieve all users (for admin).
        """
        result = await db.execute(select(User))
        users = result.scalars().all()
        return [UserResponse.from_orm(user) for user in users]

    @staticmethod
    async def update_user_dashboard_access(
        db: AsyncSession, access_data: AdminUserUpdateAccess
    ) -> Optional[UserResponse]:
        """
        Update a user's dashboard access (by admin).
        """
        user = await AuthService.get_user_by_whatsapp(db, access_data.whatsapp_number)
        if not user:
            logger.error(
                f"User {access_data.whatsapp_number} not found for updating access."
            )
            return None

        if user.is_admin:
            logger.warning(
                f"Admin user {access_data.whatsapp_number} dashboard access cannot be changed."
            )
            return None

        await db.execute(
            update(User)
            .where(User.whatsapp_number == access_data.whatsapp_number)
            .values(has_dashboard_access=access_data.has_dashboard_access)
        )
        await db.commit()
        await db.refresh(user)  # Refresh to get updated values
        logger.info(
            f"Updated dashboard access for user {user.whatsapp_number} to {user.has_dashboard_access}"
        )
        return UserResponse.from_orm(user)

    @staticmethod
    async def ensure_admin_exists(db: AsyncSession):
        """
        Ensures the admin user defined in .env exists, creates if not.
        This should be called at application startup.
        """
        admin_whatsapp = settings.ADMIN_WHATSAPP_NUMBER
        admin_password = settings.ADMIN_PASSWORD

        if not admin_whatsapp or not admin_password:
            logger.error(
                "Admin WhatsApp number or password not set in .env file. Cannot create admin user."
            )
            return

        admin_user = await AuthService.get_user_by_whatsapp(db, admin_whatsapp)
        if not admin_user:
            logger.info(f"Admin user {admin_whatsapp} not found. Creating admin user.")
            admin_create_data = UserCreate(
                whatsapp_number=admin_whatsapp, password=admin_password
            )
            try:
                admin_user = await AuthService.create_user(db, admin_create_data)

                if not admin_user.is_admin or not admin_user.has_dashboard_access:
                    admin_user.is_admin = True
                    admin_user.has_dashboard_access = True
                    await db.commit()
                    await db.refresh(admin_user)
                    logger.info(f"Admin user {admin_whatsapp} created and flags set.")
            except ValueError as e:
                logger.warning(
                    f"Could not create admin user, possibly already exists: {e}"
                )
            except Exception as e:
                logger.error(f"Failed to create admin user {admin_whatsapp}: {e}")
                await db.rollback()
        else:
            logger.info(f"Admin user {admin_whatsapp} already exists.")
            if not admin_user.is_admin or not admin_user.has_dashboard_access:
                admin_user.is_admin = True
                admin_user.has_dashboard_access = True
                admin_user.set_password(admin_password)
                await db.commit()
                await db.refresh(admin_user)
                logger.info(f"Admin user {admin_whatsapp} flags and password updated.")
