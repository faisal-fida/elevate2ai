from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from enum import Enum
import uuid


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    email_verified: bool = Field(default=False)
    full_name: Optional[str] = None
    role: UserRole = Field(default=UserRole.USER)
    payment_status: bool = Field(default=False)


class UserInDB(UserBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "email_verified": True,
                "full_name": "John Doe",
                "role": "user",
                "payment_status": False,
                "created_at": "2025-04-08T12:00:00Z",
            }
        }
