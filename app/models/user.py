import bcrypt
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base


class User(Base):
    """
    User model with WhatsApp number as primary identifier
    """

    __tablename__ = "users"

    whatsapp_number = Column(String(20), primary_key=True, index=True)
    hashed_password = Column(String, nullable=False)

    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    has_dashboard_access = Column(Boolean, default=False)  # Controlled by admin

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )

    def verify_password(self, plain_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), self.hashed_password.encode("utf-8")
        )

    def set_password(self, plain_password: str):
        salt = bcrypt.gensalt()
        self.hashed_password = bcrypt.hashpw(
            plain_password.encode("utf-8"), salt
        ).decode("utf-8")

    def __repr__(self):
        return f"<User whatsapp_number={self.whatsapp_number}>"
