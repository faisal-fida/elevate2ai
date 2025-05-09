from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.services.auth.session import SessionService
from app.services.common.logging import setup_logger

from app.api.auth.whatsapp import (
    get_current_active_user,
    oauth2_scheme as main_oauth2_scheme,
)
from app.models.user import User
from pydantic import BaseModel
from app.schemas import Token as TokenResponseSchema
from app.services.auth.security import verify_token

router = APIRouter(prefix="/session")

logger = setup_logger(__name__)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenResponseSchema)
async def refresh_access_token(
    refresh_request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using a refresh token.
    """
    token_data = await SessionService.refresh_session(
        db=db, refresh_token=refresh_request.refresh_token
    )

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Ensure the response matches the TokenResponseSchema structure
    return TokenResponseSchema(
        access_token=token_data["access_token"],
        token_type=token_data["token_type"],
        expires_in=token_data["expires_in"],
        refresh_token=token_data.get("refresh_token"),
    )


@router.post("/revoke")
async def revoke_current_session(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke the current active session (the one used to make this request).
    """
    token = await main_oauth2_scheme(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    payload = verify_token(token)
    session_jti = payload.get("jti")

    if not session_jti:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token does not contain a session identifier (jti).",
        )

    result = await SessionService.revoke_session_by_jti(
        db=db, session_jti=session_jti, whatsapp_number=current_user.whatsapp_number
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to revoke current session. It might have been already revoked or not found.",
        )

    return {"status": "success", "message": "Current session revoked successfully."}
