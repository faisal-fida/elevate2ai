from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.config import settings
from app.db import Base
import uuid


class Session(Base):
    """
    User session model for tracking active sessions
    """

    __tablename__ = "sessions"

    id = Column(
        String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )

    # User reference
    whatsapp_number = Column(
        String(20),
        ForeignKey("users.whatsapp_number", ondelete="CASCADE"),
        nullable=False,
    )

    # Session information
    token = Column(String(255), unique=True, index=True, nullable=False)
    refresh_token = Column(String(255), unique=True, index=True, nullable=True)

    # Device information
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 can be up to 45 chars
    device_info = Column(JSON, nullable=True)  # Store device info as JSON

    # Session status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(
        DateTime,
        default=lambda: datetime.utcnow()
        + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    last_activity = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session id={self.id}>"

    @property
    def is_expired(self):
        """Check if the session is expired"""
        return datetime.utcnow() > self.expires_at
