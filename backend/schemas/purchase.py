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
    product_id: int = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=20)
    rate: float = Field(..., gt=0)
    discount: float = Field(0, ge=0)
    tax: float = Field(0, ge=0)


class PurchaseItemUpdate(PurchaseItemCreate):
    id: Optional[int] = Field(None, gt=0)


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
    discount: float = Field(0, ge=0)
    tax: float = Field(0, ge=0)
    notes: Optional[str] = None
    items: List[PurchaseItemCreate]


class PurchaseUpdate(BaseModel):
    purchase_code: Optional[str] = None
    vendor_id: Optional[int] = None
    vendor_invoice_number: Optional[str] = None
    purchase_date: Optional[datetime] = None
    expected_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    discount: Optional[float] = Field(None, ge=0)
    tax: Optional[float] = Field(None, ge=0)
    payment_status: Optional[str] = None
    status: Optional[PurchaseStatus] = None
    notes: Optional[str] = None
    items: Optional[List[PurchaseItemUpdate]] = None


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
