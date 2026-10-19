"""
Notification model
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum


class NotificationType(str, enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    SUCCESS = "success"
    INFO = "info"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notification_type = Column(SQLEnum(NotificationType), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    module = Column(String(50))  # products, inventory, restaurants, etc.
    record_id = Column(Integer)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
