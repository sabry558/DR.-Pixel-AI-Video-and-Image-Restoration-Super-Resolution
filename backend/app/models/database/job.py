import enum
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import relationship
from app.db.base import Base


class JobType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    VIDEO_CLASSIFICATION = "video_classifier"
    IMAGE_CLASSIFICATION = "image_classifier"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    RUNNING = "running"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "job"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(Enum(JobType, name="job_type"), nullable=False)
    status = Column(Enum(JobStatus, name="job_status"), nullable=False, default=JobStatus.PENDING)
    original_name = Column(String, nullable=False)
    source_path = Column(String, nullable=False)
    target_path = Column(String, nullable=True)
    is_seen = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="jobs")