from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class AIDataBase(BaseModel):
    prompt: str
    response: Optional[str] = None
    model: str


class AIDataInDB(AIDataBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "prompt": "What is the meaning of life?",
                "response": "42",
                "model": "gpt-4",
                "created_at": "2025-04-08T12:00:00Z",
            }
        }
