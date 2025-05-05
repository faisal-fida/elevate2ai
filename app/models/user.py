from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class User(Base):
    """
    User model with WhatsApp number as primary identifier
    """

    __tablename__ = "users"

    # WhatsApp number as primary key
    whatsapp_number = Column(String(20), primary_key=True, index=True)

    # User profile information
    name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True, index=True)
    profile_picture = Column(String(255), nullable=True)

    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Dashboard access
    has_dashboard_access = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )

    # Additional metadata
    metadata_json = Column(
        Text, nullable=True
    )  # Store additional user metadata as JSON

    def __repr__(self):
        return f"<User whatsapp_number={self.whatsapp_number}>"
