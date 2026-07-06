from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime,String
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(Date, default=date.today, nullable=False)

    refresh_tokens = relationship("RefreshToken", back_populates="user")
    jobs = relationship("Job", back_populates="user")

