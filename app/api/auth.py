from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from supabase import create_client
from app.config import settings
from app.models.user import UserRole
from app.models.user import UserInDB
from app.crud.auth import AuthCRUD
from typing import Optional

router = APIRouter()
security = HTTPBearer(auto_error=False)


def get_user_dependency(require_admin: bool = False):
    async def dependency(token: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> UserInDB:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await get_current_user(token, require_admin)

    return dependency


async def get_current_user(token: HTTPAuthorizationCredentials, require_admin: bool = False) -> UserInDB:
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

        user = UserInDB(**user)

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
