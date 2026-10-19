"""
Purchase and PurchaseItem schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class PurchaseStatus(str, Enum):
    draft = "draft"
    ordered = "ordered"
    partially_received = "partially_received"
    received = "received"
    cancelled = "cancelled"


class PurchaseItemCreate(BaseModel):
    product_id: int
    quantity: float = Field(..., gt=0)
    unit: str
    rate: float = Field(..., gt=0)
    discount: float = 0
    tax: float = 0


class PurchaseItemResponse(BaseModel):
    id: int
    purchase_id: int
    product_id: int
    quantity: float
    unit: str
    rate: float
    discount: float
    tax: float
    total: float

    class Config:
        from_attributes = True


class PurchaseCreate(BaseModel):
    purchase_code: Optional[str] = None
    vendor_id: int
    vendor_invoice_number: Optional[str] = None
    purchase_date: datetime
    expected_date: Optional[datetime] = None
    discount: float = 0
    tax: float = 0
    notes: Optional[str] = None
    items: List[PurchaseItemCreate]


class PurchaseUpdate(BaseModel):
    vendor_id: Optional[int] = None
    vendor_invoice_number: Optional[str] = None
    expected_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    discount: Optional[float] = None
    tax: Optional[float] = None
    payment_status: Optional[str] = None
    status: Optional[PurchaseStatus] = None
    notes: Optional[str] = None


class PurchaseResponse(BaseModel):
    id: int
    purchase_code: str
    vendor_id: int
    vendor_invoice_number: Optional[str]
    purchase_date: datetime
    expected_date: Optional[datetime]
    received_date: Optional[datetime]
    subtotal: float
    discount: float
    tax: float
    total: float
    payment_status: str
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    items: List[PurchaseItemResponse] = []

    class Config:
        from_attributes = True
