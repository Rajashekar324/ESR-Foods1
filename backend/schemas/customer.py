"""
Retail Customer schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class CustomerCreate(BaseModel):
    customer_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    status: Optional[bool] = None


class CustomerResponse(BaseModel):
    id: int
    customer_code: str
    name: str
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    total_purchases: float
    last_purchase_date: Optional[datetime]
    status: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
