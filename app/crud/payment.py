from typing import Optional
from supabase import create_client, Client
from app.config import settings
import logging
from fastapi import HTTPException, status
from app.models.user import UserInDB
from app.crud.base import BaseCRUD

logger = logging.getLogger(__name__)
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


class PaymentCRUD(BaseCRUD):
    """CRUD operations for Payment model"""

    def __init__(self):
        super().__init__()
        self.set_table_name("users")

    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email"""
        try:
            result = supabase.table(self.table_name).select("*").eq("email", email).execute()
            if not result.data:
                return None
            return UserInDB(**result.data[0])
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing user retrieval",
            )

    async def update_payment_status(
        self, client_email: str, payment_status: bool
    ) -> Optional[UserInDB]:
        """Update payment status for a user by email"""
        try:
            client = await self.get_by_email(client_email)
            if not client:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            # Update the payment status
            update_data = {"payment_status": payment_status}
            result = (
                supabase.table(self.table_name)
                .update(update_data)
                .eq("email", client_email)
                .execute()
            )
            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to update payment status",
                )
            return UserInDB(**result.data[0])
        except Exception as e:
            self.logger.error(f"Error updating payment status for client {client_email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing payment status update",
            )
