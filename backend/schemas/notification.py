"""
Notification schemas
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum


class NotificationType(str, Enum):
    critical = "critical"
    warning = "warning"
    success = "success"
    info = "info"


class NotificationCreate(BaseModel):
    user_id: Optional[int] = None
    notification_type: NotificationType
    title: str
    message: str
    module: Optional[str] = None
    record_id: Optional[int] = None


class NotificationResponse(BaseModel):
    id: int
    user_id: Optional[int]
    notification_type: str
    title: str
    message: str
    module: Optional[str]
    record_id: Optional[int]
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
