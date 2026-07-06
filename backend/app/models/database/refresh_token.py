from datetime import datetime, timezone
from sqlalchemy import BigInteger, Column,DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    expire_at = Column(
        DateTime(timezone=True),
        nullable=False,
)

    user = relationship("User", back_populates="refresh_tokens")