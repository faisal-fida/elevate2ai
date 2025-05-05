from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.services.auth.session import SessionService
from app.services.common.logging import setup_logger
from app.api.auth.whatsapp import get_current_user
from typing import Dict, Any, Optional
from pydantic import BaseModel

# Create router
router = APIRouter(prefix="/session", tags=["session"])

# Setup logger
logger = setup_logger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/session/token")


# Models
class TokenRequest(BaseModel):
    whatsapp_number: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None


# Routes
@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # In this implementation, username is the WhatsApp number
    # We're not using password authentication, but the form requires it
    whatsapp_number = form_data.username

    # Get client info
    user_agent = request.headers.get("user-agent")
    client_host = request.client.host if request.client else None

    # Create session
    session_data = await SessionService.create_session(
        db=db,
        whatsapp_number=whatsapp_number,
        user_agent=user_agent,
        ip_address=client_host,
    )

    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": session_data["access_token"],
        "token_type": session_data["token_type"],
        "expires_in": session_data["expires_in"],
        "refresh_token": session_data.get("refresh_token"),
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    refresh_request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token
    """
    token_data = await SessionService.refresh_session(
        db=db, refresh_token=refresh_request.refresh_token
    )

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": token_data["access_token"],
        "token_type": token_data["token_type"],
        "expires_in": token_data["expires_in"],
        "refresh_token": token_data.get("refresh_token"),
    }


@router.post("/revoke")
async def revoke_session(
    request: Request,
    session_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke a session
    """
    if session_id:
        # Revoke specific session
        result = await SessionService.revoke_session(db=db, session_id=session_id)
    else:
        # Revoke all sessions except current one
        from app.services.auth.security import verify_token

        token = await oauth2_scheme(request)
        payload = verify_token(token)

        if not payload or "jti" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        result = await SessionService.revoke_all_sessions(
            db=db,
            whatsapp_number=current_user["whatsapp_number"],
            except_session_id=payload["jti"],
        )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to revoke session(s)",
        )

    return {"status": "success", "message": "Session(s) revoked"}
