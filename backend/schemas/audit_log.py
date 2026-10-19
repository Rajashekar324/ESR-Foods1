"""
Audit Log schemas
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    module: str
    record_id: Optional[int]
    previous_value: Optional[str]
    new_value: Optional[str]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
