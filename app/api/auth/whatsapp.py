from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.services.auth.whatsapp import WhatsAppAuthService
from app.services.auth.security import verify_token
from app.services.common.logging import setup_logger
from typing import Dict, Any, Optional
from pydantic import BaseModel

# Create router
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

# Setup logger
logger = setup_logger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/session/token")

# Models
class WhatsAppAuthRequest(BaseModel):
    whatsapp_number: str
    device_info: Optional[Dict[str, Any]] = None

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    profile_picture: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Dependency to get current user from token
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    payload = verify_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    from app.models.user import User
    from sqlalchemy.future import select
    
    result = await db.execute(select(User).where(User.whatsapp_number == payload["sub"]))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "whatsapp_number": user.whatsapp_number,
        "name": user.name,
        "email": user.email,
        "has_dashboard_access": user.has_dashboard_access,
        "is_verified": user.is_verified
    }

# Routes
@router.post("/authenticate", response_model=Dict[str, Any])
async def authenticate_whatsapp(
    auth_request: WhatsAppAuthRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate a user using WhatsApp number
    """
    # Get client info
    user_agent = request.headers.get("user-agent")
    client_host = request.client.host if request.client else None
    
    # Authenticate user
    result = await WhatsAppAuthService.authenticate_whatsapp(
        db=db,
        whatsapp_number=auth_request.whatsapp_number,
        user_agent=user_agent,
        ip_address=client_host,
        device_info=auth_request.device_info
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    
    return result

@router.post("/verify/{whatsapp_number}")
async def verify_whatsapp(
    whatsapp_number: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify a WhatsApp number
    """
    result = await WhatsAppAuthService.verify_whatsapp_number(
        db=db,
        whatsapp_number=whatsapp_number
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification failed"
        )
    
    return {"status": "success", "message": "WhatsApp number verified"}

@router.put("/profile", response_model=Dict[str, Any])
async def update_profile(
    profile_update: UserProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user profile
    """
    result = await WhatsAppAuthService.update_user_profile(
        db=db,
        whatsapp_number=current_user["whatsapp_number"],
        name=profile_update.name,
        email=profile_update.email,
        profile_picture=profile_update.profile_picture,
        metadata=profile_update.metadata
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile update failed"
        )
    
    return {
        "whatsapp_number": result.whatsapp_number,
        "name": result.name,
        "email": result.email,
        "profile_picture": result.profile_picture,
        "has_dashboard_access": result.has_dashboard_access,
        "is_verified": result.is_verified
    }

@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current user profile
    """
    return current_user
