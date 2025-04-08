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

    async def update_payment_status(
        self, client_email: str, payment_status: bool
    ) -> Optional[UserInDB]:
        """Update payment status for a user by email"""
        try:
            client = await self.get(client_email)
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
                )

            update_data = {"payment_status": payment_status}
            result = await self.update(client["id"], update_data)
            return UserInDB(**result)
        except Exception as e:
            self.logger.error(f"Error updating payment status for client {client_email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing payment status update",
            )
