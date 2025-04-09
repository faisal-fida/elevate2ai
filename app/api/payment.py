from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.models.user import UserInDB
from app.api.auth import get_user_dependency
from app.crud.payment import PaymentCRUD

router = APIRouter()


class PaymentStatusUpdate(BaseModel):
    client_email: str
    payment_status: bool


@router.patch("/status/", response_model=UserInDB)
async def update_payment_status(
    payment_status_update: PaymentStatusUpdate,
    user: UserInDB = Depends(get_user_dependency(require_admin=True)),
):
    """
    Update payment status for a client
    """
    payment_crud = PaymentCRUD()
    updated_user = await payment_crud.update_payment_status(
        payment_status_update.client_email, payment_status_update.payment_status
    )
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return updated_user
