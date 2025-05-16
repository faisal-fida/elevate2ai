from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    whatsapp_number: str
    password: str


class UserLogin(BaseModel):
    whatsapp_number: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None


class UserInDB(BaseModel):
    whatsapp_number: str
    is_active: bool
    is_admin: bool
    has_dashboard_access: bool

    class Config:
        from_attributes = True


class UserResponse(UserInDB):
    pass


class AdminUserUpdateAccess(BaseModel):
    whatsapp_number: str
    has_dashboard_access: bool
