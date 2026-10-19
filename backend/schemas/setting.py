"""
Setting schemas
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SettingCreate(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None


class SettingResponse(BaseModel):
    id: int
    key: str
    value: Optional[str]
    description: Optional[str]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
