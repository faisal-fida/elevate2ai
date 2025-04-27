from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.services.auth.google import GoogleOAuthService
from app.services.common.logging import setup_logger
from app.api.auth.whatsapp import get_current_user
from typing import Dict, Any, Optional
from pydantic import BaseModel
import json
import uuid

# Create router
router = APIRouter(prefix="/google", tags=["google"])

# Setup logger
logger = setup_logger(__name__)


# Models
class GoogleLinkRequest(BaseModel):
    whatsapp_number: str


# Routes
@router.get("/authorize")
async def authorize_google(
    whatsapp_number: str, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    """
    Start Google OAuth flow
    """
    # Check if user exists
    from app.models.user import User
    from sqlalchemy.future import select

    result = await db.execute(select(User).where(User.whatsapp_number == whatsapp_number))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Generate state parameter to prevent CSRF
    state = str(uuid.uuid4())

    # Store state in cookie
    state_data = {"whatsapp_number": whatsapp_number, "state": state}
    response.set_cookie(
        key="oauth_state",
        value=json.dumps(state_data),
        httponly=True,
        max_age=600,  # 10 minutes
        secure=False,  # Set to True in production with HTTPS
    )

    # Get authorization URL
    auth_url = GoogleOAuthService.get_authorization_url(state)

    if not auth_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured",
        )

    # Redirect to Google
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def google_callback(
    request: Request,
    response: Response,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth callback
    """
    # Check for errors
    if error:
        logger.error(f"Google OAuth error: {error}")
        return RedirectResponse(url="/auth/error?error=google_oauth_error")

    if not code or not state:
        logger.error("Missing code or state parameter")
        return RedirectResponse(url="/auth/error?error=missing_parameters")

    # Get state from cookie
    oauth_state = request.cookies.get("oauth_state")
    if not oauth_state:
        logger.error("Missing OAuth state cookie")
        return RedirectResponse(url="/auth/error?error=missing_state")

    try:
        state_data = json.loads(oauth_state)
        stored_state = state_data.get("state")
        whatsapp_number = state_data.get("whatsapp_number")

        if not stored_state or not whatsapp_number:
            logger.error("Invalid state data")
            return RedirectResponse(url="/auth/error?error=invalid_state")

        if stored_state != state:
            logger.error("State mismatch")
            return RedirectResponse(url="/auth/error?error=state_mismatch")

        # Exchange code for tokens
        token_data = await GoogleOAuthService.exchange_code_for_tokens(code)

        if not token_data or "access_token" not in token_data:
            logger.error("Failed to exchange code for tokens")
            return RedirectResponse(url="/auth/error?error=token_exchange_failed")

        # Get user info
        user_info = await GoogleOAuthService.get_user_info(token_data["access_token"])

        if not user_info or "sub" not in user_info:
            logger.error("Failed to get user info")
            return RedirectResponse(url="/auth/error?error=user_info_failed")

        # Link Google account
        from datetime import datetime, timedelta

        token_expiry = None
        if "expires_in" in token_data:
            token_expiry = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

        result = await GoogleOAuthService.link_google_account(
            db=db,
            whatsapp_number=whatsapp_number,
            google_user_id=user_info["sub"],
            google_email=user_info.get("email", ""),
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_expiry=token_expiry,
            user_info=user_info,
        )

        if not result:
            logger.error("Failed to link Google account")
            return RedirectResponse(url="/auth/error?error=account_linking_failed")

        # Clear state cookie
        response.delete_cookie(key="oauth_state")

        # Redirect to success page
        return RedirectResponse(url="/auth/success?provider=google")

    except Exception as e:
        logger.error(f"Error in Google callback: {e}")
        return RedirectResponse(url="/auth/error?error=callback_error")


@router.post("/unlink")
async def unlink_google(
    current_user: Dict[str, Any] = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Unlink Google account
    """
    result = await GoogleOAuthService.unlink_google_account(
        db=db, whatsapp_number=current_user["whatsapp_number"]
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to unlink Google account"
        )

    return {"status": "success", "message": "Google account unlinked"}
