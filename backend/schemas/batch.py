"""
Product Batch schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class BatchStatus(str, Enum):
    normal = "normal"
    expiring_soon = "expiring_soon"
    expired = "expired"


class BatchCreate(BaseModel):
    batch_number: str = Field(..., max_length=50)
    product_id: int
    vendor_id: int
    purchase_date: datetime
    received_date: datetime
    quantity: float = Field(..., gt=0)
    purchase_rate: float = Field(..., gt=0)
    manufacturing_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    storage_location: Optional[str] = None


class BatchResponse(BaseModel):
    id: int
    batch_number: str
    product_id: int
    vendor_id: int
    purchase_date: datetime
    received_date: datetime
    quantity: float
    remaining_quantity: float
    purchase_rate: float
    manufacturing_date: Optional[datetime]
    expiry_date: Optional[datetime]
    storage_location: Optional[str]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
