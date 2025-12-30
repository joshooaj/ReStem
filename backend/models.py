"""Database models for users, credits, and jobs."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
import enum
from database import Base


class JobStatus(enum.Enum):
    """Job processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """User account with authentication and credit balance."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    credits = Column(Float, default=0.0, nullable=False)
    is_admin = Column(Integer, default=0, nullable=False)  # 0 = regular user, 1 = admin
    active = Column(Integer, default=1, nullable=False)  # 0 = disabled, 1 = active
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("CreditTransaction", back_populates="user", cascade="all, delete-orphan")


class CreditTransaction(Base):
    """Credit purchase and usage history."""
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)  # Positive for purchase, negative for usage
    balance_after = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    reference = Column(String, nullable=True)  # Payment ID, job ID, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="transactions")


class Job(Base):
    """Audio separation job."""
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    model = Column(String, default="htdemucs", nullable=False)
    stem_count = Column(Integer, default=4, nullable=False)  # 2 or 4 stems
    two_stem_type = Column(String, nullable=True)  # vocals, drums, bass (only for 2-stem mode)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    cost = Column(Float, default=1.0, nullable=False)  # Credits deducted
    archived = Column(Integer, default=0, nullable=False)  # 0 = active, 1 = archived (files deleted)
    demucs_command = Column(Text, nullable=True)  # Full demucs CLI command used
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="jobs")
