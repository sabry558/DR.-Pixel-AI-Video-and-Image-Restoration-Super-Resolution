from datetime import date, datetime

from sqlalchemy import BigInteger, Column,DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from db.base import Base

class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expire_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")