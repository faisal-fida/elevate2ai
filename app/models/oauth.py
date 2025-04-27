from sqlalchemy import Column, String, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class OAuthConnection(Base):
    """
    OAuth connection model for linking external accounts
    """
    __tablename__ = "oauth_connections"

    id = Column(String(36), primary_key=True, index=True)
    
    # User reference
    whatsapp_number = Column(String(20), ForeignKey("users.whatsapp_number", ondelete="CASCADE"), nullable=False)
    
    # OAuth provider information
    provider = Column(String(20), nullable=False)  # e.g., "google", "facebook"
    provider_user_id = Column(String(100), nullable=False)
    provider_email = Column(String(100), nullable=True)
    
    # OAuth tokens
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="oauth_connections")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('provider', 'provider_user_id', name='uq_provider_user_id'),
    )
    
    def __repr__(self):
        return f"<OAuthConnection id={self.id} provider={self.provider}>"
