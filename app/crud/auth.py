from fastapi import HTTPException, status
from typing import Any
from app.crud.base import BaseCRUD
from app.models.user import UserInDB


class AuthCRUD(BaseCRUD):
    """CRUD operations for User model"""

    def __init__(self):
        super().__init__()
        self.set_table_name("users")

    async def create_from_auth(self, auth_user: Any) -> UserInDB:
        """Create or get user in public.users table from auth user data"""
        try:
            existing_user = await self.get(auth_user.id)
            if existing_user:
                return UserInDB(**existing_user)

            user_data = {
                "id": auth_user.id,
                "email": auth_user.email,
                "email_verified": getattr(auth_user, 'email_verified', False),
                "full_name": auth_user.user_metadata.get("full_name") if auth_user.user_metadata else None,
                "role": "user",
                "payment_status": False,
                "created_at": auth_user.created_at.isoformat() if getattr(auth_user, 'created_at', None) else None,
            }

            result = await self.create(user_data)
            return UserInDB(**result)
        except Exception as e:
            self.logger.error(f"Error creating user from auth: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing user creation",
            )
