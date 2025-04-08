from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from supabase import create_client
from datetime import datetime
from app.config import settings
from app.models.user import UserRole
from app.models.user import UserInDB
from app.crud.auth import AuthCRUD

router = APIRouter()
security = HTTPBearer()


def get_user_dependency(require_admin: bool = False):
    async def dependency(token: str = Depends(security)) -> UserInDB:
        return await get_current_user(token, require_admin)

    return dependency


async def get_current_user(token: str, require_admin: bool = False) -> UserInDB:
    """Get current user using Supabase Auth API"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify token with Supabase JWT secret
        payload = jwt.decode(
            token.credentials,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception

        # Get user using Supabase Auth API
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        auth_response = supabase.auth.get_user(token.credentials)
        if auth_response.user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Sync user with public.users table
        user_crud = AuthCRUD()
        user = await user_crud.get(auth_response.user.id)
        if not user:
            print("User not found in database, creating new user")
            user = await user_crud.create_from_auth(auth_response.user)

        print("User found:", user)

        # Update UserInDB with latest auth data
        user.email_verified = auth_response.user.email_confirmed_at is not None
        user.full_name = auth_response.user.user_metadata.get("full_name")
        user.avatar_url = auth_response.user.user_metadata.get("picture")
        user.provider = auth_response.user.app_metadata.get("provider")
        user.confirmed_at = auth_response.user.confirmed_at
        user.last_sign_in_at = (
            datetime.fromisoformat(str(auth_response.user.last_sign_in_at))
            if auth_response.user.last_sign_in_at
            else None
        )
        user.updated_at = auth_response.user.updated_at

        if require_admin and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
            )
        return user

    except JWTError:
        raise credentials_exception


@router.get("/users/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(get_user_dependency())):
    return current_user
