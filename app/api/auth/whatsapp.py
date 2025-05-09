from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.services.auth.whatsapp import AuthService  # Renamed service
from app.services.auth.security import verify_token
from app.services.common.logging import setup_logger
from typing import Dict, Any, List
from app.schemas import UserCreate, UserResponse, AdminUserUpdateAccess, UserLogin
from app.models.user import User

router = APIRouter()

logger = setup_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/token")


async def get_current_active_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token)
    if not payload or "sub" not in payload:
        raise credentials_exception

    whatsapp_number: str = payload.get("sub")
    if whatsapp_number is None:
        raise credentials_exception

    user = await AuthService.get_user_by_whatsapp(db, whatsapp_number=whatsapp_number)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create new user.
    """
    existing_user = await AuthService.get_user_by_whatsapp(
        db, whatsapp_number=user_in.whatsapp_number
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this WhatsApp number already exists.",
        )
    try:
        user = await AuthService.create_user(db=db, user_data=user_in)
        return user
    except (
        ValueError
    ) as e:  # Catch potential errors from service like "User already exists"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error during user registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not register user.",
        )


@router.post("/login", response_model=Dict[str, Any])  # Combined user and session info
async def login_for_access_token_custom(
    request: Request,  # Keep request for IP/User-Agent
    form_data: UserLogin,  # Use Pydantic model for login
    db: AsyncSession = Depends(get_db),
):
    """
    Login for existing user, returns access token, refresh token, and user info.
    If user does not exist, they are created.
    """
    user_agent = request.headers.get("user-agent")
    client_host = request.client.host if request.client else None

    auth_result = await AuthService.authenticate_user(
        db=db,
        whatsapp_number=form_data.whatsapp_number,
        password=form_data.password,
        user_agent=user_agent,
        ip_address=client_host,
        # device_info can be added if needed from request
    )

    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect WhatsApp number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check dashboard access
    if not auth_result["user"]["has_dashboard_access"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dashboard access denied for this user.",
        )

    return auth_result  # Contains user and session dicts


@router.get("/admin/users", response_model=List[UserResponse])
async def read_users_admin(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Retrieve all users. (Admin only)
    """
    users = await AuthService.get_all_users(db)
    return users


@router.patch("/admin/users/access", response_model=UserResponse)
async def update_user_access_admin(
    access_update: AdminUserUpdateAccess,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Update a user's dashboard access. (Admin only)
    """
    updated_user = await AuthService.update_user_dashboard_access(
        db=db, access_data=access_update
    )
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with WhatsApp number {access_update.whatsapp_number} not found or access update failed.",
        )
    return updated_user
