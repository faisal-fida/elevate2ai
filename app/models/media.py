from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class MediaBase(BaseModel):
    file_name: str
    file_path: str
    file_size: int
    file_type: str


class MediaInDB(MediaBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "example.jpg",
                "file_path": "/uploads/example.jpg",
                "file_size": 1024,
                "file_type": "image/jpeg",
                "created_at": "2025-04-08T12:00:00Z",
            }
        }
